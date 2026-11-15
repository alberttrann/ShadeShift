"use client";

import { useEffect, useRef, useState } from "react";
import {
  AttributionControl,
  GeoJSONSource,
  Map as MapLibreMap,
  NavigationControl,
  Popup,
  setWorkerUrl,
  type ExpressionSpecification,
  type StyleSpecification,
} from "maplibre-gl";
import type {
  CellMapFeatureCollectionDto,
  MapMode,
} from "@shadeshift/contracts";
import type { FeatureCollection } from "geojson";
import {
  loadClassifierMetadata,
  type ClassifierMetadata,
  type ContextLayer,
} from "../lib/classifier";
import type {
  GlobalSurfaceLayer,
  GlobalSurfaceStatus,
} from "./SurfaceLayers";

type Props = {
  data: CellMapFeatureCollectionDto;
  mode: MapMode;
  selectedCellId: string | null;
  contextLayer: ContextLayer;
  globalSurfaceLayer: GlobalSurfaceLayer;
  onGlobalSurfaceStatusChange: (status: GlobalSurfaceStatus) => void;
  onSelectCell: (cellId: string) => void;
};

type BasemapStatus = "local" | "loading" | "connected" | "unavailable";

const localStyle: StyleSpecification = {
  version: 8,
  sources: {},
  layers: [
    {
      id: "background",
      type: "background",
      paint: { "background-color": "#07111b" },
    },
  ],
};

function planningFillOpacity(
  globalSurfaceLayer: GlobalSurfaceLayer,
): number {
  if (globalSurfaceLayer === "landcover") return 0.025;
  if (globalSurfaceLayer === "vegToBuilt") return 0.055;
  return 0.50;
}

function fillColor(mode: MapMode): ExpressionSpecification {
  if (mode === "evidence") {
    return [
      "match",
      ["get", "evidenceGrade"],
      "A",
      "#2BC99A",
      "B",
      "#E9B64B",
      "C",
      "#EF7582",
      "#536273",
    ];
  }

  const field =
    mode === "priority"
      ? "priorityScore"
      : mode === "heat"
        ? "heatScore"
        : "greeningNeed";

  const palette: readonly [string, string, string, string] =
    mode === "greening"
      ? ["#2E6065", "#44A07A", "#D4AE49", "#EE7456"]
      : ["#315C80", "#328C92", "#D3AF49", "#EF7057"];

  return [
    "interpolate",
    ["linear"],
    ["coalesce", ["get", field], 0],
    0,
    palette[0],
    0.45,
    palette[1],
    0.72,
    palette[2],
    1,
    palette[3],
  ];
}

function geoBounds(
  collection: CellMapFeatureCollectionDto,
): [[number, number], [number, number]] | null {
  const coords: [number, number][] = [];

  const collect = (value: unknown) => {
    if (
      Array.isArray(value) &&
      value.length >= 2 &&
      typeof value[0] === "number" &&
      typeof value[1] === "number"
    ) {
      coords.push([value[0], value[1]]);
      return;
    }
    if (Array.isArray(value)) value.forEach(collect);
  };

  collection.features.forEach((feature) =>
    collect(feature.geometry.coordinates),
  );

  if (!coords.length) return null;

  const xs = coords.map((c) => c[0]);
  const ys = coords.map((c) => c[1]);

  return [
    [Math.min(...xs), Math.min(...ys)],
    [Math.max(...xs), Math.max(...ys)],
  ];
}

function firstSymbolLayerId(map: MapLibreMap): string | undefined {
  return map
    .getStyle()
    .layers?.find((layer) => layer.type === "symbol")?.id;
}

function declutterBasemap(map: MapLibreMap) {
  for (const layer of map.getStyle().layers ?? []) {
    if (layer.type !== "symbol") continue;

    const id = layer.id.toLowerCase();
    const lowValue =
      /(poi|housenumber|house-number|neighbou?rhood|suburb|village|hamlet|quarter|block|building-label|road-minor|minor-road)/.test(
        id,
      );

    try {
      if (lowValue) {
        map.setLayoutProperty(layer.id, "visibility", "none");
      } else {
        map.setPaintProperty(layer.id, "text-opacity", 0.76);
      }
    } catch {}
  }
}

function addScienceLayers(
  map: MapLibreMap,
  data: CellMapFeatureCollectionDto,
  mode: MapMode,
  externalStyleLoaded: boolean,
) {
  if (map.getSource("cells")) return;

  map.addSource("cells", {
    type: "geojson",
    data: data as FeatureCollection,
    promoteId: "cellId",
  });

  const beforeLabels = externalStyleLoaded
    ? firstSymbolLayerId(map)
    : undefined;

  map.addLayer(
    {
      id: "cells-fill",
      type: "fill",
      source: "cells",
      filter: ["==", ["get", "eligible"], true],
      paint: {
        "fill-color": fillColor(mode),
        "fill-opacity": planningFillOpacity("none"),
      },
    },
    beforeLabels,
  );

  map.addLayer(
    {
      id: "cells-unranked",
      type: "fill",
      source: "cells",
      filter: ["!=", ["get", "eligible"], true],
      paint: {
        "fill-color": "#536273",
        "fill-opacity": 0.065,
      },
    },
    beforeLabels,
  );

  map.addLayer(
    {
      id: "cells-line",
      type: "line",
      source: "cells",
      paint: {
        "line-color": [
          "case",
          ["==", ["get", "eligible"], true],
          "rgba(238,245,249,0.30)",
          "rgba(148,163,184,0.14)",
        ],
        "line-width": 0.58,
      },
    },
    beforeLabels,
  );

  map.addLayer(
    {
      id: "top10-outline",
      type: "line",
      source: "cells",
      filter: [
        "all",
        ["==", ["get", "eligible"], true],
        [">=", ["get", "priorityRank"], 1],
        ["<=", ["get", "priorityRank"], 10],
      ],
      layout: {
        visibility: mode === "priority" ? "visible" : "none",
      },
      paint: {
        "line-color": "rgba(255,255,255,0.82)",
        "line-width": 1.55,
      },
    },
    beforeLabels,
  );

  if (externalStyleLoaded) {
    map.addLayer({
      id: "top10-rank",
      type: "symbol",
      source: "cells",
      filter: [
        "all",
        ["==", ["get", "eligible"], true],
        [">=", ["get", "priorityRank"], 1],
        ["<=", ["get", "priorityRank"], 10],
      ],
      layout: {
        visibility: mode === "priority" ? "visible" : "none",
        "text-field": [
          "concat",
          "#",
          ["to-string", ["get", "priorityRank"]],
        ],
        "text-size": 11,
        "text-allow-overlap": true,
      },
      paint: {
        "text-color": "#ffffff",
        "text-halo-color": "#07111b",
        "text-halo-width": 2,
      },
    });
  }

  map.addLayer({
    id: "selected-fill",
    type: "fill",
    source: "cells",
    filter: ["==", ["get", "cellId"], "__none__"],
    paint: {
      "fill-color": "#ffffff",
      "fill-opacity": 0.055,
    },
  });

  map.addLayer({
    id: "selected-outline",
    type: "line",
    source: "cells",
    filter: ["==", ["get", "cellId"], "__none__"],
    paint: {
      "line-color": "#ffffff",
      "line-width": 3.15,
    },
  });
}

function removeImageLayer(
  map: MapLibreMap,
  layerId: string,
  sourceId: string,
) {
  if (map.getLayer(layerId)) map.removeLayer(layerId);
  if (map.getSource(sourceId)) map.removeSource(sourceId);
}


async function loadFreshClassifierMetadata(): Promise<ClassifierMetadata | null> {
  try {
    const response = await fetch("/data/classifier/metadata.json", {
      cache: "no-store",
      headers: { "Cache-Control": "no-cache" },
    });
    if (!response.ok) return null;
    return (await response.json()) as ClassifierMetadata;
  } catch {
    return null;
  }
}

async function assetIsReachable(url: string): Promise<boolean> {
  try {
    const response = await fetch(url, {
      cache: "no-store",
      headers: { "Cache-Control": "no-cache" },
    });
    return response.ok;
  } catch {
    return false;
  }
}

function modeHoverLine(mode: MapMode, props: Record<string, unknown>) {
  if (mode === "priority") {
    return `Priority ${Number(props.priorityScore).toFixed(3)}`;
  }
  if (mode === "heat") {
    return `Heat percentile ${Math.round(Number(props.heatScore) * 100)}`;
  }
  if (mode === "greening") {
    return `Greening need ${Math.round(Number(props.greeningNeed) * 100)}%`;
  }
  return `Evidence grade ${String(props.evidenceGrade ?? "—")}`;
}

export function MapView({
  data,
  mode,
  selectedCellId,
  contextLayer,
  globalSurfaceLayer,
  onGlobalSurfaceStatusChange,
  onSelectCell,
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const fallbackTriggeredRef = useRef(false);
  const handlersRegisteredRef = useRef(false);
  const fittedRef = useRef(false);
  const currentModeRef = useRef(mode);
  const dataRef = useRef(data);
  const classifierMetaRef = useRef<ClassifierMetadata | null>(null);

  const [basemapStatus, setBasemapStatus] =
    useState<BasemapStatus>("local");

  currentModeRef.current = mode;
  dataRef.current = data;

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    setWorkerUrl(
      new URL(
        "maplibre-gl/dist/maplibre-gl-worker.mjs",
        import.meta.url,
      ).toString(),
    );

    const mapTilerKey =
      process.env.NEXT_PUBLIC_MAPTILER_API_KEY?.trim() ?? "";

    const mapTilerStyle = mapTilerKey
      ? `https://api.maptiler.com/maps/dataviz-v4-dark/style.json?key=${encodeURIComponent(
          mapTilerKey,
        )}`
      : null;

    setBasemapStatus(mapTilerStyle ? "loading" : "local");

    const map = new MapLibreMap({
      container: containerRef.current,
      style: mapTilerStyle ?? localStyle,
      center: [106.735, 10.8],
      zoom: 13,
      attributionControl: false,
      pitchWithRotate: false,
      dragRotate: false,
      maxPitch: 0,
    });

    map.addControl(
      new NavigationControl({
        showCompass: false,
        visualizePitch: false,
      }),
      "bottom-left",
    );

    map.addControl(
      new AttributionControl({ compact: true }),
      "bottom-right",
    );

    const registerHandlers = () => {
      if (handlersRegisteredRef.current) return;
      handlersRegisteredRef.current = true;

      const popup = new Popup({
        closeButton: false,
        closeOnClick: false,
        offset: 10,
        className: "cellHoverPopup",
      });

      map.on("mousemove", "cells-fill", (event) => {
        const props = event.features?.[0]?.properties;
        if (!props || !event.lngLat) return;

        const rank =
          typeof props.priorityRank === "number"
            ? `Priority #${props.priorityRank}`
            : "Ranked cell";

        popup
          .setLngLat(event.lngLat)
          .setHTML(
            `<div class="hoverCard">
              <strong>${props.cellId}</strong>
              <span>${rank}</span>
              <small>${modeHoverLine(
                currentModeRef.current,
                props,
              )}</small>
            </div>`,
          )
          .addTo(map);
      });

      map.on("mouseleave", "cells-fill", () => popup.remove());

      map.on("click", "cells-fill", (event) => {
        const cellId = event.features?.[0]?.properties?.cellId;
        if (typeof cellId === "string") onSelectCell(cellId);
      });

      map.on("mouseenter", "cells-fill", () => {
        map.getCanvas().style.cursor = "pointer";
      });

      map.on("mouseleave", "cells-fill", () => {
        map.getCanvas().style.cursor = "";
      });
    };

    map.on("style.load", () => {
      const externalStyleLoaded =
        Boolean(mapTilerStyle) && !fallbackTriggeredRef.current;

      if (externalStyleLoaded) declutterBasemap(map);

      addScienceLayers(
        map,
        dataRef.current,
        currentModeRef.current,
        externalStyleLoaded,
      );

      registerHandlers();

      if (!fittedRef.current) {
        const bounds = geoBounds(dataRef.current);
        if (bounds) {
          map.fitBounds(bounds, {
            padding: 52,
            duration: 0,
            maxZoom: 15.2,
          });
        }
        fittedRef.current = true;
      }

      setBasemapStatus(
        externalStyleLoaded
          ? "connected"
          : mapTilerStyle
            ? "unavailable"
            : "local",
      );
    });

    map.on("error", (event) => {
      const message =
        event.error instanceof Error
          ? event.error.message
          : String(event.error ?? "");

      const externalFailure =
        message.includes("Failed to fetch") ||
        message.includes("AJAXError") ||
        message.includes("401") ||
        message.includes("403") ||
        message.includes("NetworkError");

      if (
        mapTilerStyle &&
        !fallbackTriggeredRef.current &&
        !map.getSource("cells") &&
        externalFailure
      ) {
        fallbackTriggeredRef.current = true;
        setBasemapStatus("unavailable");
        map.setStyle(localStyle);
        return;
      }

      if (mapTilerStyle && externalFailure) {
        setBasemapStatus("unavailable");
        return;
      }

      console.error("MapLibre error:", event.error);
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map?.getSource("cells")) return;

    (map.getSource("cells") as GeoJSONSource).setData(
      data as FeatureCollection,
    );
  }, [data]);

  // Single authoritative owner for the 500 m planning choropleth.
  // Async raster loading must never leave the planning map faded.
  useEffect(() => {
    const map = mapRef.current;
    if (!map?.getLayer("cells-fill")) return;

    map.setPaintProperty(
      "cells-fill",
      "fill-color",
      fillColor(mode),
    );

    map.setPaintProperty(
      "cells-fill",
      "fill-opacity",
      planningFillOpacity(globalSurfaceLayer),
    );

    const priorityVisibility =
      mode === "priority" &&
      globalSurfaceLayer === "none"
        ? "visible"
        : "none";

    if (map.getLayer("top10-rank")) {
      map.setLayoutProperty(
        "top10-rank",
        "visibility",
        priorityVisibility,
      );
    }

    if (map.getLayer("top10-outline")) {
      map.setLayoutProperty(
        "top10-outline",
        "visibility",
        priorityVisibility,
      );
    }
  }, [mode, globalSurfaceLayer]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map?.getLayer("selected-outline")) return;

    const filter: ExpressionSpecification = selectedCellId
      ? ["==", ["get", "cellId"], selectedCellId]
      : ["==", ["get", "cellId"], "__none__"];

    map.setFilter("selected-fill", filter);
    map.setFilter("selected-outline", filter);
  }, [selectedCellId]);

  // Whole-AOI surface evidence. This deliberately bypasses the shared
  // metadata promise so a freshly regenerated global export is visible after
  // restart instead of silently reusing legacy per-cell-only metadata.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    let cancelled = false;

    const apply = async () => {
      if (cancelled || !map.isStyleLoaded()) return;

      removeImageLayer(
        map,
        "global-classifier-context",
        "global-classifier-context-source",
      );

      if (globalSurfaceLayer === "none") {
        onGlobalSurfaceStatusChange("idle");
        return;
      }

      onGlobalSurfaceStatusChange("loading");

      const metadata = await loadFreshClassifierMetadata();
      if (cancelled) return;

      const global = metadata?.global;
      if (!global) {
        onGlobalSurfaceStatusChange("error");
        return;
      }

      classifierMetaRef.current = metadata;

      const url =
        globalSurfaceLayer === "landcover"
          ? global.landcover_url
          : global.veg_to_built_url;

      if (!(await assetIsReachable(url))) {
        if (!cancelled) onGlobalSurfaceStatusChange("error");
        return;
      }
      if (cancelled) return;

      map.addSource("global-classifier-context-source", {
        type: "image",
        url,
        coordinates: global.coordinates,
      });

      map.addLayer(
        {
          id: "global-classifier-context",
          type: "raster",
          source: "global-classifier-context-source",
          paint: {
            "raster-opacity":
              globalSurfaceLayer === "landcover" ? 0.93 : 0.98,
            "raster-resampling": "nearest",
          },
        },
        firstSymbolLayerId(map),
      );

      onGlobalSurfaceStatusChange("ready");
    };

    if (map.isStyleLoaded()) {
      void apply();
    } else {
      map.once("style.load", apply);
    }

    return () => {
      cancelled = true;
      map.off("style.load", apply);
      if (map.isStyleLoaded()) {
        removeImageLayer(
          map,
          "global-classifier-context",
          "global-classifier-context-source",
        );
      }
    };
  }, [globalSurfaceLayer, onGlobalSurfaceStatusChange]);

  // Selected-cell evidence lens (only when global layer is off).
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const apply = async () => {
      removeImageLayer(
        map,
        "selected-classifier-context",
        "selected-classifier-context-source",
      );

      if (
        globalSurfaceLayer !== "none" ||
        contextLayer === "none" ||
        !selectedCellId
      ) {
        return;
      }

      if (!classifierMetaRef.current) {
        classifierMetaRef.current =
          await loadClassifierMetadata();
      }

      const cell =
        classifierMetaRef.current?.cells[selectedCellId];

      if (!cell) return;

      if (
        contextLayer === "vegToBuilt" &&
        cell.counts.veg_to_built === 0
      ) {
        return;
      }

      map.addSource("selected-classifier-context-source", {
        type: "image",
        url:
          contextLayer === "landcover"
            ? cell.landcover_url
            : cell.veg_to_built_url,
        coordinates: cell.coordinates,
      });

      map.addLayer(
        {
          id: "selected-classifier-context",
          type: "raster",
          source: "selected-classifier-context-source",
          paint: {
            "raster-opacity":
              contextLayer === "landcover" ? 0.94 : 0.98,
            "raster-resampling": "nearest",
          },
        },
        firstSymbolLayerId(map),
      );
    };

    void apply();

    return () => {
      if (map.isStyleLoaded()) {
        removeImageLayer(
          map,
          "selected-classifier-context",
          "selected-classifier-context-source",
        );
      }
    };
  }, [contextLayer, selectedCellId, globalSurfaceLayer]);

  return (
    <>
      <div ref={containerRef} className="mapCanvas" />

      <div className={`basemapStatus basemap-${basemapStatus}`}>
        <span className="basemapDot" />
        {basemapStatus === "connected"
          ? "Map context on"
          : basemapStatus === "loading"
            ? "Loading map context"
            : basemapStatus === "unavailable"
              ? "Map context unavailable · analysis unaffected"
              : "Local analysis view"}
      </div>
    </>
  );
}

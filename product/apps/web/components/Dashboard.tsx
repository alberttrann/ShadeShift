"use client";

import { useEffect, useMemo, useState } from "react";
import type {
  CellDetailDto,
  CellMapFeatureCollectionDto,
  MapMode,
  MetaDto,
  MethodologyDto,
  PriorityListItemDto,
} from "@shadeshift/contracts";
import { api } from "../lib/api";
import {
  loadClassifierMetadata,
  type ClassifierMetadata,
  type ContextLayer,
} from "../lib/classifier";
import { DetailPanel } from "./DetailPanel";
import { JudgeBriefing } from "./JudgeBriefing";
import { MapLegend } from "./MapLegend";
import { MapView } from "./MapView";
import { MethodologyDrawer } from "./MethodologyDrawer";
import { ShadeShiftMark } from "./ShadeShiftMark";
import {
  SurfaceLayers,
  type GlobalSurfaceLayer,
  type GlobalSurfaceStatus,
} from "./SurfaceLayers";
import { TopList } from "./TopList";

const MODES: {
  id: MapMode;
  number: string;
  label: string;
  question: string;
}[] = [
  {
    id: "priority",
    number: "01",
    label: "Priority",
    question: "Where should planners investigate first?",
  },
  {
    id: "heat",
    number: "02",
    label: "Heat",
    question: "Where is persistent daytime heat stronger?",
  },
  {
    id: "greening",
    number: "03",
    label: "Greening",
    question: "Where is reliable vegetation most limited?",
  },
  {
    id: "evidence",
    number: "04",
    label: "Evidence",
    question: "Where is the supporting evidence stronger?",
  },
];

export function Dashboard() {
  const [meta, setMeta] = useState<MetaDto | null>(null);
  const [cells, setCells] =
    useState<CellMapFeatureCollectionDto | null>(null);
  const [top, setTop] = useState<PriorityListItemDto[]>([]);
  const [strongTop, setStrongTop] =
    useState<PriorityListItemDto[]>([]);
  const [methodology, setMethodology] =
    useState<MethodologyDto | null>(null);
  const [classifierMeta, setClassifierMeta] =
    useState<ClassifierMetadata | null>(null);

  const [mode, setMode] = useState<MapMode>("priority");
  const [contextLayer, setContextLayer] =
    useState<ContextLayer>("none");
  const [globalSurfaceLayer, setGlobalSurfaceLayer] =
    useState<GlobalSurfaceLayer>("none");
  const [surfaceMenuOpen, setSurfaceMenuOpen] = useState(false);
  const [globalSurfaceStatus, setGlobalSurfaceStatus] =
    useState<GlobalSurfaceStatus>("idle");

  const [shortlistOpen, setShortlistOpen] = useState(false);
  const [strongShortlist, setStrongShortlist] = useState(false);
  const [briefingOpen, setBriefingOpen] = useState(false);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selected, setSelected] = useState<CellDetailDto | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [methodOpen, setMethodOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.meta(),
      api.cells(),
      api.top(false),
      api.top(true),
      api.methodology(),
      loadClassifierMetadata(),
    ])
      .then(([m, c, t, st, md, classifier]) => {
        setMeta(m);
        setCells(c);
        setTop(t);
        setStrongTop(st);
        setMethodology(md);
        setClassifierMeta(classifier);

        if (t[0]) void selectCell(t[0].cellId);

        try {
          if (sessionStorage.getItem("shadeshift-v2-briefing") !== "1") {
            setBriefingOpen(true);
          }
        } catch {
          setBriefingOpen(true);
        }
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : String(err));
      });
  }, []);

  const selectedClassifier = useMemo(() => {
    if (!selectedId || !classifierMeta) return null;
    return classifierMeta.cells[selectedId] ?? null;
  }, [selectedId, classifierMeta]);

  useEffect(() => {
    if (globalSurfaceLayer !== "none") {
      setContextLayer("none");
    }
  }, [globalSurfaceLayer]);

  useEffect(() => {
    if (
      contextLayer === "vegToBuilt" &&
      selectedClassifier &&
      selectedClassifier.counts.veg_to_built === 0
    ) {
      setContextLayer("none");
    }
  }, [selectedId, selectedClassifier, contextLayer]);

  function closeBriefing() {
    setBriefingOpen(false);
    try {
      sessionStorage.setItem("shadeshift-v2-briefing", "1");
    } catch {}
  }

  function enterProduct() {
    setMode("priority");
    setGlobalSurfaceLayer("none");
    setContextLayer("none");
    const first = top[0];
    if (first) void selectCell(first.cellId);
    closeBriefing();
  }

  async function selectCell(id: string) {
    setSelectedId(id);
    setDetailLoading(true);

    try {
      setSelected(await api.cell(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setDetailLoading(false);
    }
  }

  if (error) {
    return (
      <main className="fatal">
        <h1>ShadeShift</h1>
        <p>Could not load the evidence product.</p>
        <pre>{error}</pre>
      </main>
    );
  }

  if (!cells || !meta) {
    return (
      <main className="loadingScreen">
        <ShadeShiftMark size={52} />
        <p>Loading planning evidence…</p>
      </main>
    );
  }

  const activeMode = MODES.find((item) => item.id === mode)!;

  return (
    <main className="appShell">
      <header className="header">
        <div className="brand">
          <ShadeShiftMark size={40} compact />
          <div>
            <div className="brandRow">
              <h1>ShadeShift</h1>
              <span className="pilotPill">HCMC PILOT</span>
            </div>
            <span>
              Local Thủ Đức experiment · heat, vegetation, and evidence quality
            </span>
          </div>
        </div>

        <div className="headerMeta">
          <div className="headerStat">
            <strong>{meta.eligibleCells}</strong>
            <span>ranked cells</span>
          </div>

          <button
            className="headerAction"
            onClick={() => setBriefingOpen(true)}
          >
            <span className="actionDot" />
            Project story
          </button>

          <button
            className="headerAction"
            onClick={() => setMethodOpen(true)}
          >
            Method
          </button>
        </div>
      </header>

      <section className="workspace">
        <div className="mapPane">
          <MapView
            data={cells}
            mode={mode}
            selectedCellId={selectedId}
            contextLayer={contextLayer}
            globalSurfaceLayer={globalSurfaceLayer}
            onGlobalSurfaceStatusChange={setGlobalSurfaceStatus}
            onSelectCell={selectCell}
          />

          <div className="questionDock panel">
            <div className="questionDockLead">
              <span>EXPLORE THE PILOT</span>
              <strong>{activeMode.question}</strong>
            </div>

            <div className="dockActions">
              <button
                className="topPriorityButton"
                onClick={() => setShortlistOpen(true)}
              >
                <span className="rankGlyph">#</span>
                <span>Top priorities</span>
              </button>

              <SurfaceLayers
                open={surfaceMenuOpen}
                value={globalSurfaceLayer}
                status={globalSurfaceStatus}
                onOpenChange={setSurfaceMenuOpen}
                onChange={(value) => {
                  setGlobalSurfaceLayer(value);
                  if (value === "none") {
                    setGlobalSurfaceStatus("idle");
                  }
                  setSurfaceMenuOpen(false);
                }}
              />
            </div>

            <div className="questionTabs">
              {MODES.map((item) => (
                <button
                  key={item.id}
                  className={mode === item.id ? "active" : ""}
                  onClick={() => {
                    setMode(item.id);
                    setGlobalSurfaceLayer("none");
                    setGlobalSurfaceStatus("idle");
                  }}
                >
                  <small>{item.number}</small>
                  <span>{item.label}</span>
                </button>
              ))}
            </div>
          </div>

          {shortlistOpen && (
            <>
              <div
                className="shortlistBackdrop"
                onClick={() => setShortlistOpen(false)}
              />
              <TopList
                items={top}
                strongItems={strongTop}
                selectedCellId={selectedId}
                strongEvidenceOnly={strongShortlist}
                onStrongEvidenceOnlyChange={setStrongShortlist}
                onSelect={selectCell}
                onClose={() => setShortlistOpen(false)}
              />
            </>
          )}

          <MapLegend mode={mode} />

          {globalSurfaceLayer === "landcover" && (
            <div className="globalLayerLegend panel">
              <strong>Whole-pilot · 10 m land cover</strong>
              <span><i className="ctxVeg" /> vegetation</span>
              <span><i className="ctxBuilt" /> built</span>
              <span><i className="ctxWater" /> water</span>
            </div>
          )}

          {globalSurfaceLayer === "vegToBuilt" && (
            <div className="globalLayerLegend panel">
              <strong>Whole-pilot · historical support</strong>
              <span>
                <i className="ctxV2B" />
                reliable vegetation→built
              </span>
              <small>support only · not in priority score</small>
            </div>
          )}

          {globalSurfaceLayer === "none" &&
            contextLayer === "landcover" &&
            selectedId && (
              <div className="contextLegend panel">
                <strong>{selectedId} · 10 m land cover</strong>
                <span><i className="ctxVeg" /> vegetation</span>
                <span><i className="ctxBuilt" /> built</span>
                <span><i className="ctxWater" /> water</span>
              </div>
            )}

          {globalSurfaceLayer === "none" &&
            contextLayer === "vegToBuilt" &&
            selectedId && (
              <div className="contextLegend panel">
                <strong>{selectedId} · historical support</strong>
                <span>
                  <i className="ctxV2B" />
                  reliable vegetation→built
                </span>
              </div>
            )}
        </div>

        <DetailPanel
          cell={selected}
          loading={detailLoading}
          eligibleCount={meta.eligibleCells}
          classifierContext={selectedClassifier}
          contextLayer={contextLayer}
          onContextLayerChange={(layer) => {
            setGlobalSurfaceLayer("none");
            setContextLayer(layer);
          }}
          activeMapMode={mode}
          onMapModeChange={(nextMode) => {
            setGlobalSurfaceLayer("none");
            setMode(nextMode);
          }}
        />
      </section>

      <JudgeBriefing
        meta={meta}
        topCell={top[0] ?? null}
        open={briefingOpen}
        onEnter={enterProduct}
        onSkip={closeBriefing}
      />

      <MethodologyDrawer
        methodology={methodology}
        open={methodOpen}
        onClose={() => setMethodOpen(false)}
      />
    </main>
  );
}

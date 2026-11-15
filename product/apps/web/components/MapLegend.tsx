"use client";

import type { MapMode } from "@shadeshift/contracts";

export function MapLegend({ mode }: { mode: MapMode }) {
  if (mode === "evidence") {
    return (
      <div className="mapLegend panel">
        <strong>Evidence strength</strong>
        <div className="legendCats">
          <span><i className="gradeDot dotA" /> A · strong</span>
          <span><i className="gradeDot dotB" /> B · caveated</span>
          <span><i className="gradeDot dotC" /> C · limited</span>
        </div>
      </div>
    );
  }

  const copy = {
    priority: {
      title: "Investigation priority",
      low: "Lower",
      high: "Higher priority",
    },
    heat: {
      title: "Persistent daytime heat",
      low: "Lower rank",
      high: "Higher rank",
    },
    greening: {
      title: "Greening need",
      low: "Lower need",
      high: "Higher need",
    },
  }[mode];

  return (
    <div className="mapLegend panel">
      <strong>{copy.title}</strong>
      <div className={`legendGradient legend-${mode}`} />
      <div className="legendScale">
        <span>{copy.low}</span>
        <span>{copy.high}</span>
      </div>
    </div>
  );
}

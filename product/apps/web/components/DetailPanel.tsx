"use client";

import { useEffect, useMemo, useState } from "react";
import type {
  CellDetailDto,
  MapMode,
} from "@shadeshift/contracts";
import type {
  CellClassifierContext,
  ContextLayer,
} from "../lib/classifier";

function pct(value: number | null, digits = 0) {
  if (value === null) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

function percentile(value: number | null) {
  if (value === null) return "—";
  return `${Math.round(value * 100)}th percentile`;
}

function gradePhrase(grade: string | null) {
  if (grade === "A") return "strong supporting evidence";
  if (grade === "B") return "usable evidence with caveats";
  if (grade === "C") return "limited supporting evidence";
  return "ungraded evidence";
}

type CellPattern = {
  label: string;
  tone: "overlap" | "heat" | "green" | "mixed";
  summary: string;
  implication: string;
};

function describePattern(cell: CellDetailDto): CellPattern {
  const heat = cell.heat.score;
  const green = cell.landCover.greeningNeed;

  if (heat === null || green === null) {
    return {
      label: "Incomplete comparison",
      tone: "mixed",
      summary:
        "One of the two core signals is unavailable, so this cell should be interpreted from the evidence panel rather than from the combined pattern alone.",
      implication:
        "Treat this cell as an investigation candidate with incomplete core context.",
    };
  }

  const delta = heat - green;

  if (heat >= 0.75 && green >= 0.75) {
    return {
      label: "Heat + greening overlap",
      tone: "overlap",
      summary:
        "Both signals are high relative to the pilot: persistent daytime heat and limited vegetation coincide in the same 500 m cell.",
      implication:
        "This is the clearest kind of ShadeShift candidate for follow-up investigation.",
    };
  }

  if (delta >= 0.15) {
    return {
      label: "Heat-led candidate",
      tone: "heat",
      summary:
        "Heat is the stronger local signal here. Vegetation deficit contributes, but it is not the main reason this cell rises in the ranking.",
      implication:
        "A planner should first ask what local surfaces or land uses are driving the repeatable heat pattern.",
    };
  }

  if (delta <= -0.15) {
    return {
      label: "Greening-led candidate",
      tone: "green",
      summary:
        "Vegetation deficit is the stronger local signal here. This cell is not among the pilot's strongest heat cases.",
      implication:
        "This is more useful as a low-vegetation investigation target than as evidence of an extreme heat hotspot.",
    };
  }

  return {
    label: "Mixed-signal candidate",
    tone: "mixed",
    summary:
      "Neither signal dominates. The cell enters the shortlist through a moderate combination of persistent heat and greening need.",
    implication:
      "Interpret the two signals together rather than treating either one as decisive.",
  };
}

function humanReason(reason: string) {
  const normalized = reason.toLowerCase();

  if (normalized.includes("persistent") && normalized.includes("thermal")) {
    return "Persistent daytime heat is elevated relative to the pilot.";
  }
  if (
    normalized.includes("built-dominant") ||
    normalized.includes("low vegetation") ||
    normalized.includes("limited vegetation")
  ) {
    return "Reliable land-cover evidence is built-dominant with limited vegetation.";
  }
  if (normalized.includes("hot-quartile")) {
    return "The cell repeatedly appears in the hottest quarter on observed dates.";
  }
  if (
    normalized.includes("moderate/guarded") ||
    normalized.includes("qa agreement") ||
    normalized.includes("stricter quality")
  ) {
    return "The heat pattern remains similar under stricter quality screening.";
  }
  if (normalized.includes("partial edge")) {
    return "This is an edge cell with only partial overlap of the study footprint.";
  }
  if (normalized.includes("historical") && normalized.includes("vegetation")) {
    return "Reliable historical vegetation→built transition evidence is present.";
  }

  return reason;
}

function strengthLabel(value: string | null) {
  return value ? value.replaceAll("_", " ") : "Unavailable";
}

function caveatLabel(value: string) {
  const labels: Record<string, string> = {
    limited_core_scene_count:
      "Only 3 of the 5 core Landsat dates are usable in this cell.",
    insufficient_paired_guarded_support:
      "Too few stricter-QA dates are available for full corroboration.",
    partial_spatial_footprint:
      "This edge cell only partially overlaps the study footprint.",
    paired_qa_disagreement:
      "The heat ranking changes more than expected under stricter QA.",
    temporal_rank_instability:
      "The heat ranking is sensitive to which observation date is omitted.",
  };

  return labels[value] ?? value.replaceAll("_", " ");
}

function evidenceInterpretation(cell: CellDetailDto) {
  const sceneCount = cell.heat.sceneCount;
  const recurrence = cell.heat.hotRecurrence;
  const loo = cell.heat.looMedianRange;
  const qaGap = cell.heat.pairedQaConsensusGap;

  const statements: string[] = [];

  if (sceneCount >= 5) {
    statements.push("All five core Landsat dates contribute to this cell.");
  } else if (sceneCount >= 3) {
    statements.push(
      `${sceneCount} of 5 core Landsat dates contribute; temporal coverage is usable but incomplete.`,
    );
  }

  if (recurrence !== null) {
    if (recurrence >= 0.75) {
      statements.push(
        "It repeatedly appears in the hottest quarter of the pilot across dates.",
      );
    } else if (recurrence === 0) {
      statements.push(
        "It never enters the hottest quarter, so this is not a recurrent extreme-heat cell.",
      );
    } else {
      statements.push(
        `It appears in the hottest quarter on ${Math.round(
          recurrence * 100,
        )}% of usable core dates.`,
      );
    }
  }

  if (loo !== null) {
    statements.push(
      `Removing one core date at a time shifts the median heat rank by about ${(
        loo * 100
      ).toFixed(1)} percentage points across the tested range.`,
    );
  }

  if (qaGap !== null && qaGap <= 0.03) {
    statements.push(
      "The stricter-QA comparison produces nearly the same heat rank.",
    );
  }

  return statements;
}

export function DetailPanel({
  cell,
  loading,
  eligibleCount = 51,
  classifierContext,
  contextLayer,
  onContextLayerChange,
  activeMapMode,
  onMapModeChange,
}: {
  cell: CellDetailDto | null;
  loading: boolean;
  eligibleCount?: number;
  classifierContext: CellClassifierContext | null;
  contextLayer: ContextLayer;
  onContextLayerChange: (layer: ContextLayer) => void;
  activeMapMode: MapMode;
  onMapModeChange: (mode: MapMode) => void;
}) {
  const [tab, setTab] = useState<"decision" | "evidence">("decision");

  useEffect(() => {
    setTab("decision");
  }, [cell?.cellId]);

  if (loading) {
    return <aside className="detailPanel panel">Loading local evidence…</aside>;
  }

  if (!cell) {
    return (
      <aside className="detailPanel panel emptyState">
        <div className="eyebrow">LOCAL EXPLORATION</div>
        <h2>Select a ranked cell</h2>
        <p>
          Pick a 500 m planning cell to see what kind of local pattern it
          represents, what evidence supports it, and where that evidence is
          limited.
        </p>
      </aside>
    );
  }

  const historyCount =
    classifierContext?.counts.veg_to_built ?? 0;

  const pattern = describePattern(cell);

  return (
    <aside className="detailPanel panel">
      <div className="detailHeader">
        <div>
          <div className="eyebrow">LOCAL CELL · {cell.cellId}</div>
          <h2>Priority #{cell.priority.rank}</h2>
          <div className="rankContext">
            #{cell.priority.rank} of {eligibleCount} eligible cells in this
            pilot
          </div>
        </div>

        <div
          className={`gradeBadge grade${
            cell.evidence.grade ?? "Unknown"
          }`}
          title="Evidence strength; it does not modify priority rank."
        >
          {cell.evidence.grade ?? "—"}
          <small>evidence</small>
        </div>
      </div>

      <div className={`patternCard pattern-${pattern.tone}`}>
        <span>LOCAL PATTERN</span>
        <strong>{pattern.label}</strong>
        <p>{pattern.summary}</p>
      </div>

      <div className="detailTabs">
        <button
          className={tab === "decision" ? "active" : ""}
          onClick={() => setTab("decision")}
        >
          Interpret
        </button>
        <button
          className={tab === "evidence" ? "active" : ""}
          onClick={() => setTab("evidence")}
        >
          Evidence
        </button>
      </div>

      {tab === "decision" ? (
        <DecisionTab
          cell={cell}
          pattern={pattern}
          classifierContext={classifierContext}
          contextLayer={contextLayer}
          onContextLayerChange={onContextLayerChange}
          activeMapMode={activeMapMode}
          onMapModeChange={onMapModeChange}
          onOpenEvidence={() => setTab("evidence")}
        />
      ) : (
        <EvidenceTab
          cell={cell}
          historyCount={historyCount}
        />
      )}
    </aside>
  );
}

function DecisionTab({
  cell,
  pattern,
  classifierContext,
  contextLayer,
  onContextLayerChange,
  activeMapMode,
  onMapModeChange,
  onOpenEvidence,
}: {
  cell: CellDetailDto;
  pattern: CellPattern;
  classifierContext: CellClassifierContext | null;
  contextLayer: ContextLayer;
  onContextLayerChange: (layer: ContextLayer) => void;
  activeMapMode: MapMode;
  onMapModeChange: (mode: MapMode) => void;
  onOpenEvidence: () => void;
}) {
  const historyCount =
    classifierContext?.counts.veg_to_built ?? 0;

  const supportedLandcover =
    classifierContext
      ? classifierContext.counts.vegetation +
        classifierContext.counts.built +
        classifierContext.counts.water
      : 0;

  const reasons = useMemo(
    () => cell.reason.slice(0, 4).map(humanReason),
    [cell.reason],
  );

  return (
    <>
      <div className="decisionHero">
        <div>
          <span>Relative local priority</span>
          <strong>{cell.priority.score?.toFixed(3) ?? "—"}</strong>
        </div>
        <p>
          A transparent pilot-area ranking, not a citywide heat-risk
          probability.
        </p>
      </div>

      <section className="factorSection">
        <div className="sectionStoryHead">
          <span>01 · TWO DIFFERENT SIGNALS</span>
          <h3>What is actually pulling this cell upward?</h3>
        </div>

        <Factor
          label="Persistent daytime heat"
          value={percentile(cell.heat.score)}
          raw={cell.heat.score}
          weight="60% of core score"
          kind="heat"
        />

        <Factor
          label="Current greening need"
          value={pct(cell.landCover.greeningNeed)}
          raw={cell.landCover.greeningNeed}
          weight="40% of core score"
          kind="green"
        />

        <div className="patternImplication">
          <strong>{pattern.label}</strong>
          <span>{pattern.implication}</span>
        </div>

        <div className="driverActions">
          <button
            className={activeMapMode === "heat" ? "active" : ""}
            onClick={() => onMapModeChange("heat")}
          >
            See heat across the pilot
          </button>
          <button
            className={activeMapMode === "greening" ? "active" : ""}
            onClick={() => onMapModeChange("greening")}
          >
            See greening across the pilot
          </button>
        </div>
      </section>

      <section>
        <div className="sectionStoryHead">
          <span>02 · WHY IT SURVIVED THE RANKING</span>
          <h3>What evidence makes this cell worth keeping?</h3>
        </div>

        <ul className="plainReasons">
          {reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      </section>

      <section>
        <div className="sectionStoryHead">
          <span>03 · LOOK BELOW THE 500 M SCORE</span>
          <h3>What does the surface evidence look like inside?</h3>
          <p>
            These are explanatory layers from the local experiment. They do not
            change this cell's priority.
          </p>
        </div>

        <div className="explainChoices">
          <button
            className={
              contextLayer === "landcover" ? "active" : ""
            }
            disabled={!classifierContext || supportedLandcover === 0}
            onClick={() =>
              onContextLayerChange(
                contextLayer === "landcover"
                  ? "none"
                  : "landcover",
              )
            }
          >
            <span className="explainIcon explainLand">10m</span>
            <strong>
              {contextLayer === "landcover"
                ? "Hide 10 m land cover"
                : "Reveal 10 m land cover"}
            </strong>
            <span>
              Inspect where reliable built, vegetation, and water pixels lie
              inside this planning cell.
            </span>
          </button>

          <button
            className={
              contextLayer === "vegToBuilt" ? "active" : ""
            }
            disabled={!classifierContext || historyCount === 0}
            onClick={() =>
              onContextLayerChange(
                contextLayer === "vegToBuilt"
                  ? "none"
                  : "vegToBuilt",
              )
            }
          >
            <span className="explainIcon explainHistory">17→25</span>
            <strong>
              {historyCount > 0
                ? contextLayer === "vegToBuilt"
                  ? "Hide historical support"
                  : "Reveal historical support"
                : "No transition signal detected"}
            </strong>
            <span>
              {historyCount > 0
                ? `${historyCount.toLocaleString()} reliable vegetation→built pixels occur inside this cell.`
                : "No reliable vegetation→built transition was detected on the jointly reliable subset."}
            </span>
          </button>
        </div>

        {classifierContext && historyCount === 0 && (
          <div className="zeroEvidenceNote">
            This is a real absence of that support signal, not a missing layer.
          </div>
        )}
      </section>

      <section className="nextQuestionSection">
        <div className="sectionStoryHead">
          <span>04 · DO NOT HIDE THE CAVEATS</span>
          <h3>How much of this pattern survived our checks?</h3>
        </div>
        <p>
          Grade {cell.evidence.grade ?? "—"} means {gradePhrase(
            cell.evidence.grade,
          )}. Evidence strength stays separate from the priority score.
        </p>
        <button onClick={onOpenEvidence}>
          Read the evidence trail →
        </button>
      </section>
    </>
  );
}

function EvidenceTab({
  cell,
  historyCount,
}: {
  cell: CellDetailDto;
  historyCount: number;
}) {
  const interpretation = evidenceInterpretation(cell);

  return (
    <>
      <section className="evidenceNarrative">
        <span>WHAT SURVIVED THE CHECKS?</span>
        <h3>
          Grade {cell.evidence.grade ?? "—"} is about support, not importance.
        </h3>
        <p>
          This tab explains why the cell received its evidence grade. None of
          these diagnostics secretly re-rank the cell.
        </p>
      </section>

      <section>
        <div className="sectionStoryHead">
          <span>01 · THERMAL REPEATABILITY</span>
          <h3>Did the heat pattern hold across dates?</h3>
        </div>

        <div className="evidenceStoryList">
          {interpretation.map((statement) => (
            <div key={statement}>
              <i />
              <span>{statement}</span>
            </div>
          ))}
        </div>

        <div className="metricGrid">
          <Metric
            label="Usable core dates"
            value={`${cell.heat.sceneCount} / 5`}
            hint="pre-selected Landsat dates"
          />
          <Metric
            label="Hottest-quarter recurrence"
            value={pct(cell.heat.hotRecurrence)}
            hint="supporting interpretation"
          />
          <Metric
            label="Leave-one-date-out range"
            value={pct(cell.heat.looMedianRange, 1)}
            hint="temporal sensitivity"
          />
          <Metric
            label="Stricter-QA rank gap"
            value={pct(cell.heat.pairedQaConsensusGap, 1)}
            hint="same-date QA comparison"
          />
        </div>
      </section>

      <section>
        <div className="sectionStoryHead">
          <span>02 · COVERAGE & SUPPORT</span>
          <h3>Is this cell spatially well-supported?</h3>
        </div>

        <div className="strengthRows">
          <Strength
            label="Temporal stability"
            value={cell.evidence.temporalStrength}
          />
          <Strength
            label="QA corroboration"
            value={cell.evidence.qaStrength}
          />
          <Strength
            label="Spatial support"
            value={cell.evidence.spatialStrength}
          />
          <Strength
            label="Pilot-footprint overlap"
            value={pct(cell.evidence.footprintOverlap)}
            raw
          />
        </div>
      </section>

      <section>
        <div className="sectionStoryHead">
          <span>03 · CURRENT & HISTORICAL SURFACE</span>
          <h3>What does land-cover evidence contribute?</h3>
          <p>
            Greening need comes from current reliable built-vs-vegetation
            evidence. Historical change is shown only as supporting context.
          </p>
        </div>

        <div className="metricGrid">
          <Metric
            label="Reliable built share"
            value={pct(cell.landCover.builtFraction)}
          />
          <Metric
            label="Reliable vegetation share"
            value={pct(cell.landCover.vegetationFraction)}
          />
          <Metric
            label="Current greening need"
            value={pct(cell.landCover.greeningNeed)}
            hint="core score input"
          />
          <Metric
            label="Reliable veg→built pixels"
            value={historyCount.toLocaleString()}
            hint="support only · not scored"
          />
        </div>
      </section>

      <section>
        <div className="sectionStoryHead">
          <span>04 · CAVEATS</span>
          <h3>What should a planner keep in mind?</h3>
        </div>

        {cell.evidence.caveats.length ? (
          <div className="caveatBox">
            {cell.evidence.caveats.map((c) => (
              <span key={c}>{caveatLabel(c)}</span>
            ))}
          </div>
        ) : (
          <div className="cleanEvidence">
            No material evidence caveats were detected for this cell under the
            current pilot rules.
          </div>
        )}

        <div className="evidenceBoundary">
          <strong>Still not a prescription</strong>
          <span>
            This evidence can prioritize investigation. It does not identify a
            legal planting site, predict degrees of cooling, or prove a causal
            effect.
          </span>
        </div>
      </section>
    </>
  );
}

function Factor({
  label,
  value,
  raw,
  weight,
  kind,
}: {
  label: string;
  value: string;
  raw: number | null;
  weight: string;
  kind: "heat" | "green";
}) {
  return (
    <div className="factor">
      <div className="factorHeader">
        <div>
          <strong>{label}</strong>
          <span>{weight}</span>
        </div>
        <b>{value}</b>
      </div>
      <div className="factorTrack">
        <div
          className={`factorFill factor-${kind}`}
          style={{
            width: `${Math.max(0, Math.min(1, raw ?? 0)) * 100}%`,
          }}
        />
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
      {hint && <small>{hint}</small>}
    </div>
  );
}

function Strength({
  label,
  value,
  raw = false,
}: {
  label: string;
  value: string | null;
  raw?: boolean;
}) {
  return (
    <div className="strengthRow">
      <span>{label}</span>
      <strong>{raw ? value : strengthLabel(value)}</strong>
    </div>
  );
}

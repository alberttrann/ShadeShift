"use client";

import type {
  MetaDto,
  PriorityListItemDto,
} from "@shadeshift/contracts";
import { ShadeShiftMark } from "./ShadeShiftMark";

function pct(value: number) {
  return `${Math.round(value * 100)}%`;
}

function percentile(value: number) {
  return `${Math.round(value * 100)}th percentile`;
}

export function JudgeBriefing({
  meta,
  topCell,
  open,
  onEnter,
  onSkip,
}: {
  meta: MetaDto;
  topCell: PriorityListItemDto | null;
  open: boolean;
  onEnter: () => void;
  onSkip: () => void;
}) {
  if (!open || !topCell) return null;

  const gradeA = meta.evidenceGrades.A ?? 0;

  return (
    <div className="briefingBackdrop">
      <div className="briefingGlow briefingGlowA" />
      <div className="briefingGlow briefingGlowB" />

      <main className="briefingShell">
        <header className="briefingBrand">
          <ShadeShiftMark size={56} />
          <div>
            <strong>ShadeShift</strong>
            <span>NASA Space Apps 2026 · local Thủ Đức experiment</span>
          </div>
        </header>

        <section className="experimentHero">
          <div className="experimentHeroCopy">
            <div className="briefingKicker">
              LOCAL EXPERIMENT · ~14.7 KM² · THỦ ĐỨC
            </div>

            <h1>
              We started small:
              <em>
                which satellite signals could we actually trust for heat and
                shade?
              </em>
            </h1>

            <p className="experimentLead">
              ShadeShift is not a citywide heat-risk model. It is a deliberately
              limited local experiment: take one mixed urban patch, test several
              Earth-observation signals, reject the ones that do not hold up,
              and see whether the surviving evidence can support a useful
              planning shortlist.
            </p>

            <div className="experimentWhy">
              <div>
                <span>WHY THIS PILOT?</span>
                <strong>A compact, mixed urban test bed</strong>
                <p>
                  The pilot contains dense built surfaces, vegetation, major
                  waterways, and sharp local transitions within a footprint
                  small enough to audit cell by cell.
                </p>
              </div>

              <div>
                <span>WHAT WE WANTED TO LEARN</span>
                <strong>Not “where is hottest?” — but “what survives scrutiny?”</strong>
                <p>
                  Heat, vegetation, historical change, spatial support, and
                  uncertainty were treated as separate pieces of evidence
                  rather than collapsed into one opaque prediction.
                </p>
              </div>
            </div>

            <div className="briefingActions">
              <button className="briefingPrimary" onClick={onEnter}>
                Explore the local experiment
                <span>→</span>
              </button>

              <button className="briefingSecondary" onClick={onSkip}>
                Skip to map
              </button>
            </div>
          </div>

          <aside className="experimentFinding">
            <div className="experimentFindingEyebrow">
              WHAT SURVIVED THE PIPELINE
            </div>

            <div className="findingHeader">
              <div>
                <span>TOP LOCAL INVESTIGATION CANDIDATE</span>
                <strong>
                  #{topCell.priorityRank} · {topCell.cellId}
                </strong>
              </div>
              <div className={`findingGrade grade${topCell.evidence.grade}`}>
                {topCell.evidence.grade}
                <small>evidence</small>
              </div>
            </div>

            <div className="findingScore">
              <span>relative investigation priority</span>
              <strong>{topCell.priorityScore.toFixed(3)}</strong>
            </div>

            <div className="findingSignals">
              <Signal
                index="01"
                label="Persistent daytime heat"
                value={percentile(topCell.heatScore)}
                amount={topCell.heatScore}
                kind="heat"
              />
              <Signal
                index="02"
                label="Current greening need"
                value={pct(topCell.greeningNeed)}
                amount={topCell.greeningNeed}
                kind="green"
              />
            </div>

            <div className="findingGrid">
              <div>
                <strong>{meta.totalCells}</strong>
                <span>500 m candidate cells</span>
              </div>
              <div>
                <strong>{meta.eligibleCells}</strong>
                <span>cells survived eligibility</span>
              </div>
              <div>
                <strong>{gradeA}</strong>
                <span>Grade-A evidence cells</span>
              </div>
            </div>

            <div className="findingTakeaway">
              <span>LOCAL INSIGHT</span>
              <p>
                Heat and vegetation deficit did <b>not</b> collapse into the
                same map. The useful signal was their overlap — and whether the
                evidence behind each cell remained stable enough to trust.
              </p>
            </div>
          </aside>
        </section>

        <section className="experimentJourney">
          <div className="journeyIntro">
            <span>THE JOURNEY MATTERS</span>
            <h2>
              The product came from a sequence of tests, failures, and
              corrections — not from choosing a pretty final layer.
            </h2>
          </div>

          <div className="journeyRail">
            <Journey
              number="01"
              status="SURVIVED"
              title="Map the current surface"
              source="OlmoEarth · 10 m embeddings"
              copy="We trained a simple three-class land-cover classifier for built, vegetation, and water, then kept unsupported pixels visible as unknown instead of forcing a label everywhere."
            />

            <Journey
              number="02"
              status="REJECTED AS CORE"
              title="Try ECOSTRESS for thermal persistence"
              source="NASA ECOSTRESS"
              copy="The observations were real, but the hotspot pattern did not persist reliably across dates at 70 m or 500 m. We downgraded ECOSTRESS to contextual evidence instead of forcing it into the score."
              rejected
            />

            <Journey
              number="03"
              status="SURVIVED"
              title="Test Landsat repeatability"
              source="Landsat 8/9 Surface Temperature"
              copy="Five pre-selected core daytime acquisitions produced a repeatable 500 m spatial pattern. That became the thermal core: a multi-date percentile-rank consensus, not a single ‘best’ scene."
            />

            <Journey
              number="04"
              status="CORRECTED"
              title="Catch a spatial ranking bug"
              source="500 m planning grid audit"
              copy="A boundary audit exposed sliver cells that looked extreme only because tiny fragments overlapped the raster. We reopened the gate, required ≥50% spatial support, recomputed the ranks, and removed the false winners."
            />

            <Journey
              number="05"
              status="FROZEN"
              title="Rank only what the evidence supports"
              source="ShadeShift planning heuristic"
              copy="The final local score is intentionally transparent: 60% persistent heat + 40% current greening need. Historical change and evidence grades explain the result, but never secretly alter it."
            />
          </div>
        </section>

        <section className="experimentLessons">
          <div className="lessonPrimary">
            <span>WHAT WE ACTUALLY LEARNED</span>
            <h2>
              The useful contribution is not another heat map.
            </h2>
            <p>
              It is a workflow for asking: <b>which local signals are stable,
              which are misleading, and how do we expose that distinction to a
              planner?</b> ShadeShift keeps those decisions visible all the way
              into the interface.
            </p>
          </div>

          <div className="lessonCards">
            <article>
              <span>01</span>
              <div className="lessonCardBody">
                <strong>Hot ≠ vegetation-poor</strong>
                <p>
                  The heat and greening layers tell different stories. Some
                  cells are heat-led, some are greening-led, and only some are
                  true overlap cases.
                </p>
              </div>
            </article>
            <article>
              <span>02</span>
              <div className="lessonCardBody">
                <strong>More data is not always better</strong>
                <p>
                  ECOSTRESS was scientifically interesting, but failed our
                  persistence test. The right decision was to keep it
                  contextual instead of forcing it into the score.
                </p>
              </div>
            </article>
            <article>
              <span>03</span>
              <div className="lessonCardBody">
                <strong>Uncertainty is part of the product</strong>
                <p>
                  Evidence grades, coverage, temporal stability, and spatial
                  support remain visible instead of becoming a hidden
                  confidence score.
                </p>
              </div>
            </article>
          </div>
        </section>

        <footer className="briefingFooter experimentFooter">
          <span>
            Pilot scope: ~14.7 km² in Thủ Đức · 500 m planning cells · 10 m
            land-cover evidence.
          </span>
          <span>
            Relative investigation priority only — not a calibrated heat-risk
            probability or a tree-placement prescription.
          </span>
        </footer>
      </main>
    </div>
  );
}

function Signal({
  index,
  label,
  value,
  amount,
  kind,
}: {
  index: string;
  label: string;
  value: string;
  amount: number;
  kind: "heat" | "green";
}) {
  return (
    <div className="findingSignal">
      <div className="findingSignalTop">
        <span>{index}</span>
        <div>
          <small>{label}</small>
          <strong>{value}</strong>
        </div>
      </div>
      <div className="findingTrack">
        <div
          className={`findingFill ${kind}`}
          style={{
            width: `${Math.max(0, Math.min(1, amount)) * 100}%`,
          }}
        />
      </div>
    </div>
  );
}

function Journey({
  number,
  status,
  title,
  source,
  copy,
  rejected = false,
}: {
  number: string;
  status: string;
  title: string;
  source: string;
  copy: string;
  rejected?: boolean;
}) {
  return (
    <article className={`journeyItem ${rejected ? "rejected" : ""}`}>
      <div className="journeyNumber">{number}</div>
      <div className="journeyBody">
        <div className="journeyMeta">
          <span>{source}</span>
          <b>{status}</b>
        </div>
        <strong>{title}</strong>
        <p>{copy}</p>
      </div>
    </article>
  );
}

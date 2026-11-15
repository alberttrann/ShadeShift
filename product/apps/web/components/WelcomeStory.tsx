"use client";

import type {
  MetaDto,
  PriorityListItemDto,
} from "@shadeshift/contracts";

function pct(value: number) {
  return `${Math.round(value * 100)}%`;
}

function percentile(value: number) {
  return `${Math.round(value * 100)}th percentile`;
}

export function WelcomeStory({
  meta,
  topCell,
  open,
  onClose,
  onExploreTop,
}: {
  meta: MetaDto;
  topCell: PriorityListItemDto | null;
  open: boolean;
  onClose: () => void;
  onExploreTop: () => void;
}) {
  if (!open || !topCell) return null;

  const gradeA = meta.evidenceGrades.A ?? 0;

  return (
    <div className="storyBackdrop">
      <section className="storyCard">
        <button
          className="storyClose"
          onClick={onClose}
          aria-label="Close introduction"
        >
          ×
        </button>

        <div className="storyKicker">SHADE SHIFT · HCMC PILOT</div>

        <h1>
          Where should planners investigate urban cooling first?
        </h1>

        <p className="storyLead">
          ShadeShift combines persistent daytime heat with current greening
          need, then keeps evidence quality visible instead of hiding
          uncertainty.
        </p>

        <div className="storyFinding">
          <span>Strongest investigation candidate</span>
          <div className="storyFindingMain">
            <strong>#{topCell.priorityRank} · {topCell.cellId}</strong>
            <b>{topCell.priorityScore.toFixed(3)}</b>
          </div>

          <div className="storyFindingSignals">
            <div>
              <span>Persistent heat</span>
              <strong>{percentile(topCell.heatScore)}</strong>
            </div>
            <div>
              <span>Greening need</span>
              <strong>{pct(topCell.greeningNeed)}</strong>
            </div>
            <div>
              <span>Evidence</span>
              <strong>Grade {topCell.evidence.grade}</strong>
            </div>
          </div>
        </div>

        <div className="storySteps">
          <article>
            <div className="storyStepNumber">1</div>
            <div>
              <strong>Screen the evidence</strong>
              <p>
                {meta.totalCells} candidate 500 m cells become{" "}
                {meta.eligibleCells} ranked cells after spatial and thermal
                eligibility checks.
              </p>
            </div>
          </article>

          <article>
            <div className="storyStepNumber">2</div>
            <div>
              <strong>Rank where to look first</strong>
              <p>
                Priority combines 60% validated heat persistence with 40%
                current greening need. It is a relative planning score, not a
                risk probability.
              </p>
            </div>
          </article>

          <article>
            <div className="storyStepNumber">3</div>
            <div>
              <strong>Inspect why — and how strong the evidence is</strong>
              <p>
                {gradeA} cells have Grade-A evidence. Selected cells can be
                opened to 10 m land-cover evidence and historical
                vegetation-to-built support without changing their rank.
              </p>
            </div>
          </article>
        </div>

        <div className="storyActions">
          <button className="storyPrimary" onClick={onExploreTop}>
            Explore #{topCell.priorityRank} {topCell.cellId}
          </button>
          <button className="storySecondary" onClick={onClose}>
            Explore the map freely
          </button>
        </div>

        <small className="storyFootnote">
          Satellite evidence: Landsat 8/9 daytime thermal consensus +
          OlmoEarth-derived land-cover evidence. ECOSTRESS remains contextual
          only after failing persistence validation.
        </small>
      </section>
    </div>
  );
}

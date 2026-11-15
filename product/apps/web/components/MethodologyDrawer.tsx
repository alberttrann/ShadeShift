"use client";

import type { MethodologyDto } from "@shadeshift/contracts";

export function MethodologyDrawer({
  methodology,
  open,
  onClose,
}: {
  methodology: MethodologyDto | null;
  open: boolean;
  onClose: () => void;
}) {
  if (!open || !methodology) return null;

  return (
    <div className="drawerBackdrop" onClick={onClose}>
      <aside
        className="methodDrawer"
        onClick={(event) => event.stopPropagation()}
        aria-label="ShadeShift experiment methodology"
      >
        <button className="closeButton" onClick={onClose} aria-label="Close method panel">
          ×
        </button>

        <div className="methodHero">
          <div className="eyebrow">HOW THE LOCAL EXPERIMENT EARNED ITS RANKING</div>
          <h2>From candidate signals to a defensible shortlist.</h2>
          <p>
            ShadeShift is a small-area Thủ Đức experiment, not a citywide heat-risk model.
            The method is intentionally simple: test each signal, reject what does not hold up,
            and keep the surviving evidence visible all the way to the map.
          </p>

          <div className="methodScopeGrid">
            <div>
              <strong>~14.7 km²</strong>
              <span>pilot footprint</span>
            </div>
            <div>
              <strong>500 m</strong>
              <span>planning cells</span>
            </div>
            <div>
              <strong>10 m</strong>
              <span>land-cover evidence</span>
            </div>
          </div>
        </div>

        <section className="methodSection">
          <MethodHeading number="01" kicker="THE QUESTION" title="What are we actually trying to decide?" />
          <p>{methodology.question}</p>
          <div className="methodBoundaryNote">
            The output is a relative investigation priority within this frozen pilot — not a
            heat-health probability and not a prescription for where to plant.
          </div>
        </section>

        <section className="methodSection">
          <MethodHeading number="02" kicker="TEST THE SIGNALS" title="We did not keep every dataset we tried." />

          <div className="methodJourney">
            <MethodStep
              status="KEPT"
              tone="kept"
              title="Current surface · OlmoEarth"
              text="10 m embeddings support a transparent built / vegetation / water classifier. Unsupported pixels remain unknown instead of being forced into a class."
            />
            <MethodStep
              status="DOWNGRADED"
              tone="rejected"
              title="Nighttime thermal context · ECOSTRESS"
              text="ECOSTRESS observations were scientifically useful, but the hotspot pattern failed our temporal-persistence test. They remain contextual evidence and never enter the core score."
            />
            <MethodStep
              status="KEPT"
              tone="kept"
              title="Daytime thermal core · Landsat 8/9"
              text="Five pre-selected daytime acquisitions produced a repeatable 500 m spatial pattern, so Landsat became the validated thermal core."
            />
            <MethodStep
              status="CORRECTED"
              tone="corrected"
              title="Spatial support · boundary audit"
              text="A later audit caught sliver cells whose apparent extremes came from tiny raster overlap. We reopened the ranking and required at least 50% pilot-footprint support."
            />
          </div>
        </section>

        <section className="methodSection">
          <MethodHeading number="03" kicker="FREEZE THE CORE" title="The final score stays deliberately interpretable." />

          <div className="formulaCard">
            <span>RELATIVE PRIORITY</span>
            <div className="formulaVisual">
              <div className="formulaPart heatPart">
                <b>60%</b>
                <strong>Persistent daytime heat</strong>
                <small>multi-date Landsat rank</small>
              </div>
              <div className="formulaPlus">+</div>
              <div className="formulaPart greenPart">
                <b>40%</b>
                <strong>Greening need</strong>
                <small>built vs vegetation</small>
              </div>
            </div>
            <p>{methodology.priorityFormula}</p>
          </div>

          <div className="methodDefinitionGrid">
            <article>
              <span>DAYTIME HEAT</span>
              <p>
                {methodology.heatDefinition} The product compares relative spatial patterns;
                it does not claim independent 30 m thermal detail or exact neighborhood temperature.
              </p>
            </article>
            <article>
              <span>GREENING NEED</span>
              <p>
                Current reliable built-vs-vegetation composition is used as a simple surface
                deficit signal. It is not the same thing as tree-canopy percentage or planting feasibility.
              </p>
            </article>
          </div>
        </section>

        <section className="methodSection">
          <MethodHeading number="04" kicker="KEEP SUPPORT SEPARATE" title="Priority and confidence are not the same number." />

          <p>{methodology.evidenceDefinition}</p>

          <div className="evidenceGradeStory">
            <div>
              <b>A</b>
              <span>strong temporal, QA, and spatial support</span>
            </div>
            <div>
              <b>B</b>
              <span>usable evidence with visible caveats</span>
            </div>
            <div>
              <b>C</b>
              <span>limited support; interpret cautiously</span>
            </div>
          </div>

          <div className="supportOnlyCard">
            <strong>Supporting evidence stays supporting.</strong>
            <p>{methodology.historicalRole}</p>
            <p>{methodology.ecostressRole}</p>
          </div>
        </section>

        <section className="methodSection">
          <MethodHeading number="05" kicker="WHAT WE REFUSE TO HIDE" title="The limitations are part of the result." />

          <div className="methodLimitations">
            {methodology.limitations.map((item, index) => (
              <div key={item}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <p>{humanizeLimitation(item)}</p>
              </div>
            ))}
          </div>

          <div className="methodClosing">
            <span>THE PRINCIPLE</span>
            <strong>Use the map to decide where to investigate next — not to pretend the satellite data already made the planning decision.</strong>
          </div>
        </section>
      </aside>
    </div>
  );
}

function MethodHeading({
  number,
  kicker,
  title,
}: {
  number: string;
  kicker: string;
  title: string;
}) {
  return (
    <div className="methodHeading">
      <div>{number}</div>
      <div>
        <span>{kicker}</span>
        <h3>{title}</h3>
      </div>
    </div>
  );
}

function MethodStep({
  status,
  tone,
  title,
  text,
}: {
  status: string;
  tone: "kept" | "rejected" | "corrected";
  title: string;
  text: string;
}) {
  return (
    <article className={`methodStep methodStep-${tone}`}>
      <div className="methodStepTop">
        <strong>{title}</strong>
        <span>{status}</span>
      </div>
      <p>{text}</p>
    </article>
  );
}

function humanizeLimitation(item: string) {
  if (item.includes("weak multi-source consensus")) {
    return "The land-cover classifier was checked against weak multi-source consensus labels, not an independent human-labelled ground-truth survey.";
  }
  if (item.includes("Partial-edge")) {
    return "Edge cells are never treated as full cells by default: footprint overlap remains visible, and unsupported slivers were removed from ranking eligibility.";
  }
  if (item.includes("fewer usable Landsat dates")) {
    return "Some cells have fewer usable Landsat dates. Scene count and temporal stability remain visible rather than being collapsed into a hidden confidence score.";
  }
  if (item.includes("not a calibrated heat-health risk probability")) {
    return "The score only ranks this frozen pilot. It is not calibrated to heat-health risk and should not be extrapolated to all of HCMC.";
  }
  return item;
}

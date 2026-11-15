import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const dataDir =
  process.env.SHADE_SHIFT_DATA_DIR ??
  resolve(process.cwd(), "../public/data");

const required = [
  "planning_cells_evidence_enhanced.geojson",
  "priority_top10_evidence_enhanced.json",
  "high_confidence_priority_top10.json",
];

const missing = required.filter(
  (filename) => !existsSync(resolve(dataDir, filename)),
);

if (missing.length) {
  console.error("\nShadeShift product data preflight FAILED.");
  console.error(`Data directory: ${dataDir}`);
  console.error("Missing:");
  for (const name of missing) console.error(`  - ${name}`);
  console.error(
    "\nRun Gate C4.1 and ensure its outputs are under public/data, " +
      "or set SHADE_SHIFT_DATA_DIR to the correct folder.\n",
  );
  process.exit(2);
}

const geo = JSON.parse(
  readFileSync(
    resolve(dataDir, "planning_cells_evidence_enhanced.geojson"),
    "utf8",
  ),
);

if (geo?.type !== "FeatureCollection" || !Array.isArray(geo?.features)) {
  console.error("Enhanced planning GeoJSON is not a FeatureCollection.");
  process.exit(3);
}

const eligible = geo.features.filter(
  (f) => f?.properties?.eligible === true,
);
const grades = eligible.reduce((acc, feature) => {
  const grade = feature?.properties?.evidence_grade ?? "ungraded";
  acc[grade] = (acc[grade] ?? 0) + 1;
  return acc;
}, {});

console.log("ShadeShift product data preflight PASSED.");
console.log(`Data directory: ${dataDir}`);
console.log(`Cells: ${geo.features.length}`);
console.log(`Eligible: ${eligible.length}`);
console.log(`Grades: ${JSON.stringify(grades)}`);

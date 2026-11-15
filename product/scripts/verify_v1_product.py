from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

required = [
    "package.json",
    "apps/web/app/globals.css",
    "apps/web/app/layout.tsx",
    "apps/web/components/Dashboard.tsx",
    "apps/web/components/MapView.tsx",
    "apps/web/components/DetailPanel.tsx",
    "apps/web/components/TopList.tsx",
    "apps/web/components/MapLegend.tsx",
    "apps/web/lib/api.ts",
    "apps/web/lib/classifier.ts",
    "apps/api/src/evidence/evidence.service.ts",
]

failures = []
checks = {}

for rel in required:
    p = ROOT / rel
    ok = p.exists() and p.stat().st_size > 0
    checks[f"file:{rel}"] = ok
    if not ok:
        failures.append(f"missing required file: {rel}")

def text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")

if not failures:
    dash = text("apps/web/components/Dashboard.tsx")
    detail = text("apps/web/components/DetailPanel.tsx")
    mapview = text("apps/web/components/MapView.tsx")
    top = text("apps/web/components/TopList.tsx")

    invariants = {
        "toolbar_has_no_context_dropdown": "ContextLayers" not in dash,
        "toolbar_has_no_global_grade_filter": "Grade A only" not in dash,
        "classifier_explanation_in_detail": "Inspect this cell" in detail,
        "explicit_zero_history_state":
            "No reliable veg→built transition detected" in detail,
        "history_disabled_when_zero": "historyCount === 0" in detail,
        "grade_filter_inside_shortlist":
            "Show Grade-A evidence only" in top,
        "priority_rank_markers_priority_only":
            'mode === "priority" ? "visible" : "none"' in mapview,
        "basemap_decluttering_present": "declutterBasemap" in mapview,
        "mode_specific_hover_present": "modeHoverLine" in mapview,
        "selected_cell_classifier_source":
            "selected-classifier-context-source" in mapview,
    }

    checks.update(invariants)
    failures.extend(
        f"UX invariant failed: {name}"
        for name, passed in invariants.items()
        if not passed
    )

asset_meta = ROOT / "apps/web/public/data/classifier/metadata.json"
if asset_meta.exists():
    try:
        meta = json.loads(asset_meta.read_text(encoding="utf-8"))
        cells = meta.get("cells", {})
        checks["classifier_asset_cell_count"] = len(cells)
        if len(cells) != 51:
            failures.append(
                f"classifier metadata has {len(cells)} cells; expected 51"
            )
    except Exception as exc:
        failures.append(f"classifier metadata invalid: {exc}")
else:
    checks["classifier_assets_note"] = (
        "not bundled; run npm run prepare:classifier-layers locally"
    )

result = {
    "status": "PASS" if not failures else "FAIL",
    "checks": checks,
    "failures": failures,
}

print(json.dumps(result, indent=2))
raise SystemExit(0 if not failures else 2)

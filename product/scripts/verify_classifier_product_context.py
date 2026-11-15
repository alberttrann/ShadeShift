from __future__ import annotations

import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
asset_dir = ROOT / "apps/web/public/data/classifier"
meta_path = asset_dir / "metadata.json"

failures = []
checks = {}

required = [
    ROOT / "apps/web/components/MapView.tsx",
    ROOT / "apps/web/components/Dashboard.tsx",
    ROOT / "apps/web/components/SurfaceLayers.tsx",
    ROOT / "apps/web/components/JudgeBriefing.tsx",
    ROOT / "apps/web/components/ShadeShiftMark.tsx",
    ROOT / "apps/web/app/globals.css",
    meta_path,
]

for p in required:
    checks[str(p.relative_to(ROOT))] = {
        "exists": p.exists(),
        "bytes": p.stat().st_size if p.exists() else 0,
    }
    if not p.exists() or p.stat().st_size == 0:
        failures.append(f"missing: {p}")

if meta_path.exists():
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    cells = meta.get("cells", {})
    global_meta = meta.get("global", {})

    checks["metadata_version"] = meta.get("version")
    checks["eligible_cell_count"] = meta.get("eligible_cell_count")
    checks["cell_record_count"] = len(cells)
    checks["global_metadata_present"] = bool(global_meta)

    if len(cells) != 51:
        failures.append(
            f"expected 51 eligible cell context records, found {len(cells)}"
        )

    global_urls = [
        global_meta.get("landcover_url"),
        global_meta.get("veg_to_built_url"),
    ]

    for url in global_urls:
        if not url:
            failures.append("global classifier URL missing")
            continue
        path = ROOT / "apps/web/public" / url.lstrip("/")
        if not path.exists():
            failures.append(f"missing global asset: {path}")
        else:
            with Image.open(path) as im:
                checks[f"global:{path.name}"] = {
                    "size": list(im.size),
                    "mode": im.mode,
                }

    png_count = 0
    for cell_id, record in cells.items():
        for key in ["landcover_url", "veg_to_built_url"]:
            path = (
                ROOT
                / "apps/web/public"
                / record[key].lstrip("/")
            )
            if not path.exists():
                failures.append(f"missing {cell_id} asset: {path}")
                continue
            png_count += 1

    checks["cell_png_count"] = png_count

    if png_count != 102:
        failures.append(
            f"expected 102 selected-cell PNGs, found {png_count}"
        )

result = {
    "status": "PASS" if not failures else "FAIL",
    "checks": checks,
    "failures": failures,
}

print(json.dumps(result, indent=2))
raise SystemExit(0 if not failures else 2)

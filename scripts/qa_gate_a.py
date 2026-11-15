import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect(path: Path) -> dict:
    with rasterio.open(path) as ds:
        arr = ds.read()
        finite = np.isfinite(arr)
        pixel_all = finite.all(axis=0)
        pixel_any = finite.any(axis=0)
        data_vals = arr[finite]
        return {
            "path": str(path),
            "exists": True,
            "count": ds.count,
            "width": ds.width,
            "height": ds.height,
            "dtype": list(ds.dtypes),
            "crs": ds.crs.to_string() if ds.crs else None,
            "transform": list(ds.transform)[:6],
            "bounds": list(ds.bounds),
            "nodata": str(ds.nodata),
            "all_bands_valid_pixel_fraction": float(pixel_all.mean()),
            "any_band_valid_pixel_fraction": float(pixel_any.mean()),
            "all_nan": bool(not finite.any()),
            "finite_min": float(data_vals.min()) if data_vals.size else None,
            "finite_max": float(data_vals.max()) if data_vals.size else None,
            "sha256": sha256(path),
        }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--y2017", default="data/olmoearth_hcmc_2017_64d.tif")
    ap.add_argument("--y2025", default="data/olmoearth_hcmc_2025_64d.tif")
    ap.add_argument("--out", default="logs/gate_a_raster_qa.json")
    args = ap.parse_args()

    p17, p25 = Path(args.y2017), Path(args.y2025)
    missing = [str(p) for p in (p17, p25) if not p.exists()]
    if missing:
        result = {"gate": "A", "raster_qa_pass": False, "missing": missing}
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
        raise SystemExit(2)

    a, b = inspect(p17), inspect(p25)
    same_grid = (
        a["count"] == b["count"] == 64
        and a["width"] == b["width"]
        and a["height"] == b["height"]
        and a["crs"] == b["crs"]
        and np.allclose(a["transform"], b["transform"], rtol=0, atol=1e-9)
    )
    ranges_plausible = all(
        x["finite_min"] is not None
        and x["finite_min"] >= -1.05
        and x["finite_max"] <= 1.05
        for x in (a, b)
    )
    valid_coverage = all(x["all_bands_valid_pixel_fraction"] > 0.25 for x in (a, b))
    no_all_nan = all(not x["all_nan"] for x in (a, b))

    checks = {
        "both_64_bands": a["count"] == 64 and b["count"] == 64,
        "matching_grid": same_grid,
        "nonzero_valid_coverage": valid_coverage,
        "no_all_nan": no_all_nan,
        "dequantized_value_range_plausible": ranges_plausible,
    }
    result = {
        "gate": "A",
        "raster_qa_pass": all(checks.values()),
        "checks": checks,
        "2017": a,
        "2025": b,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["raster_qa_pass"] else 3)


if __name__ == "__main__":
    main()

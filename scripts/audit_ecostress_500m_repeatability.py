import argparse, json, math
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import from_bounds
from scipy.stats import pearsonr, spearmanr

BANDS = [
    "jan11",
    "jan19",
    "mar28",
    "mar17_holdout",
]

CORE = ["jan11", "jan19", "mar28"]

def corr(a, b, kind="pearson"):
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 5:
        return None
    if np.nanstd(a[m]) == 0 or np.nanstd(b[m]) == 0:
        return None
    if kind == "pearson":
        r = pearsonr(a[m], b[m])
    else:
        r = spearmanr(a[m], b[m])
    return {
        "n": int(m.sum()),
        "r": float(r.statistic),
        "p_value": float(r.pvalue),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--raster",
        default="data/shadeshift_gate_c1_scene_anomalies.tif"
    )
    ap.add_argument("--grid-m", type=float, default=500.0)
    ap.add_argument(
        "--out-csv",
        default="logs/gate_c1_500m_scene_anomalies.csv"
    )
    ap.add_argument(
        "--out-json",
        default="logs/gate_c1_500m_repeatability.json"
    )
    ap.add_argument("--min-valid-fraction", type=float, default=0.50)
    args = ap.parse_args()

    p = Path(args.raster)
    if not p.exists():
        raise SystemExit(f"Missing {p}")

    with rasterio.open(p) as ds:
        if ds.count != 4:
            raise SystemExit(f"Expected 4 anomaly bands, found {ds.count}")
        if ds.crs is None or ds.crs.to_string() != "EPSG:32648":
            raise SystemExit(f"Expected EPSG:32648, got {ds.crs}")

        arr = ds.read().astype("float32")
        arr[arr <= -9990] = np.nan
        bounds = ds.bounds
        transform = ds.transform

    cell = args.grid_m
    xmin = math.floor(bounds.left / cell) * cell
    ymin = math.floor(bounds.bottom / cell) * cell
    xmax = math.ceil(bounds.right / cell) * cell
    ymax = math.ceil(bounds.top / cell) * cell

    records = []
    cid = 0
    y = ymin
    while y < ymax:
        x = xmin
        while x < xmax:
            # Calculate raster row/column window covering this planning cell.
            win = from_bounds(
                x, y, x + cell, y + cell,
                transform=transform
            )
            r0 = max(0, int(math.floor(win.row_off)))
            c0 = max(0, int(math.floor(win.col_off)))
            r1 = min(arr.shape[1], int(math.ceil(win.row_off + win.height)))
            c1 = min(arr.shape[2], int(math.ceil(win.col_off + win.width)))

            if r1 > r0 and c1 > c0:
                rec = {
                    "cell_id": f"C{cid:03d}",
                    "xmin": x,
                    "ymin": y,
                    "xmax": x + cell,
                    "ymax": y + cell,
                }
                any_overlap = False
                for i, name in enumerate(BANDS):
                    v = arr[i, r0:r1, c0:c1]
                    finite = np.isfinite(v)
                    coverage = float(finite.mean()) if v.size else 0.0
                    rec[f"{name}_coverage"] = coverage
                    rec[f"{name}_median"] = (
                        float(np.nanmedian(v))
                        if coverage >= args.min_valid_fraction
                        else np.nan
                    )
                    any_overlap = any_overlap or finite.any()
                if any_overlap:
                    records.append(rec)
                    cid += 1
            x += cell
        y += cell

    df = pd.DataFrame(records)

    pair_results = {}
    for a, b in [
        ("jan11", "jan19"),
        ("jan11", "mar28"),
        ("jan19", "mar28"),
    ]:
        aa = df[f"{a}_median"].to_numpy(float)
        bb = df[f"{b}_median"].to_numpy(float)
        pair_results[f"{a}_vs_{b}"] = {
            "pearson": corr(aa, bb, "pearson"),
            "spearman": corr(aa, bb, "spearman"),
        }

    core_matrix = df[[f"{x}_median" for x in CORE]].to_numpy(float)
    core_median = np.nanmedian(core_matrix, axis=1)
    core_valid_n = np.isfinite(core_matrix).sum(axis=1)
    core_median[core_valid_n < 2] = np.nan
    df["core_median"] = core_median
    df["core_valid_scene_count"] = core_valid_n

    hold = df["mar17_holdout_median"].to_numpy(float)
    holdout_result = {
        "pearson": corr(core_median, hold, "pearson"),
        "spearman": corr(core_median, hold, "spearman"),
    }

    # Stability of the top quartile at neighborhood scale.
    complete_core = np.isfinite(core_matrix).all(axis=1)
    top_quartile = {}
    if complete_core.sum() >= 8:
        sets = {}
        for i, name in enumerate(CORE):
            vals = core_matrix[:, i]
            valid = complete_core & np.isfinite(vals)
            threshold = np.nanquantile(vals[valid], 0.75)
            sets[name] = set(np.where(valid & (vals >= threshold))[0].tolist())

        for a, b in [
            ("jan11", "jan19"),
            ("jan11", "mar28"),
            ("jan19", "mar28"),
        ]:
            union = sets[a] | sets[b]
            inter = sets[a] & sets[b]
            top_quartile[f"{a}_vs_{b}"] = {
                "intersection": len(inter),
                "union": len(union),
                "jaccard": float(len(inter) / len(union)) if union else None,
            }

    report = {
        "grid_m": cell,
        "cells": int(len(df)),
        "min_valid_fraction_per_scene_cell": args.min_valid_fraction,
        "pairwise_core_500m": pair_results,
        "core_median_vs_partial_holdout_500m": holdout_result,
        "top_quartile_hot_cell_overlap": top_quartile,
        "decision_guidance": {
            "strong": "Most 500m core Spearman/Pearson correlations >= 0.5 and top-quartile Jaccard materially above chance.",
            "moderate": "Most correlations around 0.3-0.5; use only conservative persistent-hot evidence.",
            "weak": "Correlations remain near zero/negative at 500m; ECOSTRESS should not be a core ranking term."
        }
    }

    Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out_csv, index=False)
    Path(args.out_json).write_text(
        json.dumps(report, indent=2),
        encoding="utf-8"
    )

    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()

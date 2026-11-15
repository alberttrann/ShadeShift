import json
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

LC17 = Path("outputs/landcover_2017.tif")
LC25 = Path("outputs/landcover_2025.tif")
CF17 = Path("outputs/confidence_2017.tif")
CF25 = Path("outputs/confidence_2025.tif")
OUT_JSON = Path("logs/gate_b_transition_audit.json")
OUT_CSV = Path("logs/gate_b_transition_matrix.csv")
OUT_TIF = Path("outputs/change_code_2017_2025.tif")

CLASSES = [0, 1, 2, 4]
NAMES = {0: "unknown", 1: "vegetation", 2: "built", 4: "water"}
PIXEL_AREA_KM2 = 0.0001  # 10m x 10m
HIGH_CONF = 0.80

with rasterio.open(LC17) as a, rasterio.open(LC25) as b:
    if (a.width, a.height, a.crs, a.transform) != (b.width, b.height, b.crs, b.transform):
        raise SystemExit("2017 and 2025 class rasters are not on the exact same grid.")
    x17 = a.read(1)
    x25 = b.read(1)
    profile = a.profile.copy()

with rasterio.open(CF17) as a, rasterio.open(CF25) as b:
    c17 = a.read(1)
    c25 = b.read(1)

valid = (x17 != 255) & (x25 != 255) & np.isfinite(c17) & np.isfinite(c25)
high = valid & (c17 >= HIGH_CONF) & (c25 >= HIGH_CONF)

matrix = []
for i in CLASSES:
    row = []
    for j in CLASSES:
        row.append(int(np.sum(valid & (x17 == i) & (x25 == j))))
    matrix.append(row)

df = pd.DataFrame(
    matrix,
    index=[f"2017_{NAMES[i]}" for i in CLASSES],
    columns=[f"2025_{NAMES[j]}" for j in CLASSES],
)
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUT_CSV)

high_matrix = []
for i in CLASSES:
    row = []
    for j in CLASSES:
        row.append(int(np.sum(high & (x17 == i) & (x25 == j))))
    high_matrix.append(row)

# Compact transition code: 10 * old + new.
# e.g. 12 = vegetation -> built, 21 = built -> vegetation.
code = np.full(x17.shape, 255, dtype=np.uint8)
code[valid] = (10 * x17[valid] + x25[valid]).astype(np.uint8)
profile.update(count=1, dtype="uint8", nodata=255, compress="deflate")
with rasterio.open(OUT_TIF, "w", **profile) as dst:
    dst.write(code, 1)

total = int(valid.sum())
changed = valid & (x17 != x25)
high_changed = high & (x17 != x25)

def count(a, b, mask=valid):
    return int(np.sum(mask & (x17 == a) & (x25 == b)))

report = {
    "grid_valid_pixels": total,
    "pixel_area_km2": PIXEL_AREA_KM2,
    "total_valid_area_km2": total * PIXEL_AREA_KM2,
    "confidence_threshold_for_high_conf_audit": HIGH_CONF,
    "high_conf_both_years_fraction": float(np.sum(high) / total),
    "any_class_change_pixels": int(np.sum(changed)),
    "any_class_change_fraction": float(np.sum(changed) / total),
    "high_conf_change_pixels": int(np.sum(high_changed)),
    "high_conf_change_fraction_of_all_valid": float(np.sum(high_changed) / total),
    "transition_matrix_classes": CLASSES,
    "transition_matrix": matrix,
    "high_conf_transition_matrix": high_matrix,
    "key_transitions": {
        "vegetation_to_built": {
            "pixels": count(1, 2),
            "area_km2": count(1, 2) * PIXEL_AREA_KM2,
            "high_conf_pixels": count(1, 2, high),
            "high_conf_area_km2": count(1, 2, high) * PIXEL_AREA_KM2
        },
        "built_to_vegetation": {
            "pixels": count(2, 1),
            "area_km2": count(2, 1) * PIXEL_AREA_KM2,
            "high_conf_pixels": count(2, 1, high),
            "high_conf_area_km2": count(2, 1, high) * PIXEL_AREA_KM2
        },
        "water_to_built": {
            "pixels": count(4, 2),
            "area_km2": count(4, 2) * PIXEL_AREA_KM2,
            "high_conf_pixels": count(4, 2, high),
            "high_conf_area_km2": count(4, 2, high) * PIXEL_AREA_KM2
        },
        "built_to_water": {
            "pixels": count(2, 4),
            "area_km2": count(2, 4) * PIXEL_AREA_KM2,
            "high_conf_pixels": count(2, 4, high),
            "high_conf_area_km2": count(2, 4, high) * PIXEL_AREA_KM2
        }
    },
    "warning": "A predicted transition is not automatically a verified real-world change. Use high-confidence transitions plus imagery review."
}

OUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(df)
print(json.dumps(report, indent=2))

import json
from pathlib import Path

import numpy as np
import geopandas as gpd
import rasterio
from rasterio.transform import xy
from shapely.geometry import Point

LC17 = Path("outputs/landcover_2017.tif")
LC25 = Path("outputs/landcover_2025.tif")
CF17 = Path("outputs/confidence_2017.tif")
CF25 = Path("outputs/confidence_2025.tif")
OUT = Path("labels/gate_b_targeted_visual_review.geojson")

RNG = np.random.default_rng(42)
HIGH = 0.80

with rasterio.open(LC17) as a:
    x17 = a.read(1)
    transform = a.transform
    crs = a.crs
with rasterio.open(LC25) as b:
    x25 = b.read(1)
with rasterio.open(CF17) as a:
    c17 = a.read(1)
with rasterio.open(CF25) as b:
    c25 = b.read(1)

valid = (x17 != 255) & (x25 != 255) & np.isfinite(c17) & np.isfinite(c25)

targets = [
    ("veg_to_built_high", 1, 2, True, 20),
    ("built_to_veg_high", 2, 1, True, 15),
    ("water_to_built_high", 4, 2, True, 10),
    ("built_to_water_high", 2, 4, True, 10),
    ("stable_vegetation", 1, 1, True, 10),
    ("stable_built", 2, 2, True, 10),
    ("stable_water", 4, 4, True, 10),
    ("unknown_2025", None, 0, False, 15),
]

rows = []
for category, old, new, require_high, n in targets:
    mask = valid.copy()
    if old is not None:
        mask &= (x17 == old)
    if new is not None:
        mask &= (x25 == new)
    if require_high:
        mask &= (c17 >= HIGH) & (c25 >= HIGH)

    coords = np.argwhere(mask)
    if len(coords) == 0:
        continue
    take = min(n, len(coords))
    idx = RNG.choice(len(coords), size=take, replace=False)
    for r, c in coords[idx]:
        X, Y = xy(transform, int(r), int(c), offset="center")
        rows.append({
            "category": category,
            "class_2017": int(x17[r,c]),
            "class_2025": int(x25[r,c]),
            "confidence_2017": float(c17[r,c]),
            "confidence_2025": float(c25[r,c]),
            "visual_verdict": "",
            "review_notes": "",
            "geometry": Point(X, Y)
        })

g = gpd.GeoDataFrame(rows, crs=crs)
g = g.to_crs("EPSG:4326")
OUT.parent.mkdir(parents=True, exist_ok=True)
g.to_file(OUT, driver="GeoJSON")
print(f"Wrote {len(g)} targeted review points -> {OUT}")
print(g['category'].value_counts())

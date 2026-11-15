from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from PIL import Image
from pyproj import Transformer
from rasterio.mask import mask


LC_COLORS = {
    1: (49, 166, 105, 235),   # vegetation
    2: (221, 126, 63, 225),   # built
    4: (54, 139, 214, 230),   # water
}
V2B_COLOR = (248, 102, 70, 245)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rgba_landcover(arr: np.ndarray) -> np.ndarray:
    out = np.zeros((*arr.shape, 4), dtype=np.uint8)
    for code, rgba in LC_COLORS.items():
        out[arr == code] = rgba
    return out


def rgba_v2b(arr: np.ndarray) -> np.ndarray:
    out = np.zeros((*arr.shape, 4), dtype=np.uint8)
    out[arr == 12] = V2B_COLOR
    return out


def corners_from_transform(transform, width: int, height: int, crs):
    pts = [
        transform * (0, 0),
        transform * (width, 0),
        transform * (width, height),
        transform * (0, height),
    ]
    transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    return [
        list(map(float, transformer.transform(x, y)))
        for x, y in pts
    ]


def crop_one(ds, geom):
    data, transform = mask(
        ds,
        [geom],
        crop=True,
        filled=True,
        nodata=0,
    )
    arr = data[0]
    h, w = arr.shape
    return arr, transform, w, h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--science-root", default=None)
    ap.add_argument(
        "--landcover",
        default="outputs/reliable_landcover_2025.tif",
    )
    ap.add_argument(
        "--change",
        default="outputs/reliable_change_code_2017_2025.tif",
    )
    ap.add_argument(
        "--cells",
        default="public/data/planning_cells_evidence_enhanced.geojson",
    )
    ap.add_argument(
        "--out",
        default="apps/web/public/data/classifier",
    )
    args = ap.parse_args()

    product_root = Path(__file__).resolve().parents[1]
    science_root = (
        Path(args.science_root).resolve()
        if args.science_root
        else product_root.parent.resolve()
    )

    lc_path = science_root / args.landcover
    ch_path = science_root / args.change
    cells_path = science_root / args.cells
    out_dir = (product_root / args.out).resolve()
    cell_dir = out_dir / "cells"
    cell_dir.mkdir(parents=True, exist_ok=True)

    for p in [lc_path, ch_path, cells_path]:
        if not p.exists():
            raise SystemExit(f"Missing required input: {p}")

    cells = gpd.read_file(cells_path)
    if "cell_id" not in cells.columns or "eligible" not in cells.columns:
        raise SystemExit(
            "Planning cells need cell_id and eligible properties."
        )

    eligible = cells[cells["eligible"].astype(bool)].copy()

    with rasterio.open(lc_path) as lc, rasterio.open(ch_path) as ch:
        if lc.count != 1 or ch.count != 1:
            raise SystemExit("Expected one-band Gate-B rasters.")
        if (
            lc.crs != ch.crs
            or lc.width != ch.width
            or lc.height != ch.height
            or lc.transform != ch.transform
        ):
            raise SystemExit("Land-cover and change rasters are not aligned.")

        global_lc = lc.read(1)
        global_change = ch.read(1)
        global_coords = corners_from_transform(
            lc.transform,
            lc.width,
            lc.height,
            lc.crs,
        )

        global_landcover_png = out_dir / "global_landcover_2025.png"
        global_v2b_png = out_dir / "global_veg_to_built_2017_2025.png"
        out_dir.mkdir(parents=True, exist_ok=True)

        Image.fromarray(
            rgba_landcover(global_lc),
            mode="RGBA",
        ).save(global_landcover_png, optimize=True)

        Image.fromarray(
            rgba_v2b(global_change),
            mode="RGBA",
        ).save(global_v2b_png, optimize=True)

        eligible = eligible.to_crs(lc.crs)

        cell_meta = {}

        for _, row in eligible.iterrows():
            cell_id = str(row["cell_id"])
            geom = row.geometry

            lc_arr, crop_transform, width, height = crop_one(lc, geom)
            ch_arr, ch_transform, ch_width, ch_height = crop_one(ch, geom)

            if (
                width != ch_width
                or height != ch_height
                or crop_transform != ch_transform
            ):
                raise SystemExit(
                    f"Crop alignment mismatch for {cell_id}"
                )

            coords = corners_from_transform(
                crop_transform,
                width,
                height,
                lc.crs,
            )

            lc_png = cell_dir / f"{cell_id}_landcover.png"
            v2b_png = cell_dir / f"{cell_id}_veg_to_built.png"

            Image.fromarray(
                rgba_landcover(lc_arr),
                mode="RGBA",
            ).save(lc_png, optimize=True)

            Image.fromarray(
                rgba_v2b(ch_arr),
                mode="RGBA",
            ).save(v2b_png, optimize=True)

            counts = {
                "vegetation": int((lc_arr == 1).sum()),
                "built": int((lc_arr == 2).sum()),
                "water": int((lc_arr == 4).sum()),
                "unknown_or_masked": int(
                    (~np.isin(lc_arr, [1, 2, 4])).sum()
                ),
                "veg_to_built": int((ch_arr == 12).sum()),
            }

            cell_meta[cell_id] = {
                "coordinates": coords,
                "width": width,
                "height": height,
                "landcover_url":
                    f"/data/classifier/cells/{cell_id}_landcover.png",
                "veg_to_built_url":
                    f"/data/classifier/cells/{cell_id}_veg_to_built.png",
                "counts": counts,
            }

    metadata = {
        "version": "classifier-context-v2-global-plus-cell",
        "eligible_cell_count": len(cell_meta),
        "source": {
            "landcover": {
                "path": str(lc_path),
                "sha256": sha256(lc_path),
            },
            "change": {
                "path": str(ch_path),
                "sha256": sha256(ch_path),
            },
            "planning_cells": {
                "path": str(cells_path),
                "sha256": sha256(cells_path),
            },
        },
        "global": {
            "coordinates": global_coords,
            "width": int(global_lc.shape[1]),
            "height": int(global_lc.shape[0]),
            "landcover_url":
                "/data/classifier/global_landcover_2025.png",
            "veg_to_built_url":
                "/data/classifier/global_veg_to_built_2017_2025.png",
        },
        "cells": cell_meta,
        "semantics": {
            "global_landcover": (
                "Reliable Gate-B 2025 land-cover evidence across the source "
                "raster footprint."
            ),
            "global_historical": (
                "Reliable 2017→2025 vegetation-to-built support across the "
                "jointly reliable subset. Not a core score input."
            ),
            "selected_cell": (
                "Same evidence clipped to the selected planning cell for "
                "fine-grained explanation."
            ),
        },
    }

    meta_path = out_dir / "metadata.json"
    meta_path.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "status": "PASS",
                "mode": "global-plus-selected-cell",
                "eligible_cells_exported": len(cell_meta),
                "cell_pngs": len(cell_meta) * 2,
                "global_pngs": 2,
                "metadata": str(meta_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

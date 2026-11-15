import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
import zarr
from obstore.store import S3Store
from pyproj import Transformer
from rasterio.transform import Affine

DEFAULT_BBOX = (106.715, 10.785, 106.755, 10.815)
STORE = "s3://olmoearth/olmoearth-v1-3-embeddings/embeddings.zarr"
ENDPOINT = "https://data.source.coop"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    p = argparse.ArgumentParser(description="Export ShadeShift AOI from OlmoEarth v1.3 global annual embeddings")
    p.add_argument("--year", type=int, required=True, choices=range(2017, 2026))
    p.add_argument("--bands", type=int, default=64, choices=(64, 128))
    p.add_argument("--bbox", type=float, nargs=4, metavar=("WEST", "SOUTH", "EAST", "NORTH"), default=DEFAULT_BBOX)
    p.add_argument("--out-dir", default="data")
    args = p.parse_args()

    west, south, east, north = args.bbox
    if west >= east or south >= north:
        raise SystemExit("Invalid bbox order. Expected WEST SOUTH EAST NORTH.")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / f"olmoearth_hcmc_{args.year}_{args.bands}d.tif"
    summary_path = out_dir / f"olmoearth_hcmc_{args.year}_{args.bands}d.summary.json"

    # Exact access/dequantization pattern from the official OlmoEarth export guide.
    zarr.config.set({"array.sharding_coalesce_max_gap_bytes": 0})
    s3 = S3Store.from_url(STORE, endpoint=ENDPOINT, skip_signature=True)
    root = zarr.open_group(zarr.storage.ObjectStore(s3, read_only=True), mode="r")

    zone_number = int((west + 180) // 6) + 1
    east_zone = int((east + 180) // 6) + 1
    if east_zone != zone_number:
        raise SystemExit(f"AOI crosses UTM zones {zone_number} and {east_zone}; split export before continuing.")

    zone = root[f"utm{zone_number:02d}"]
    crs = zone.attrs["proj:code"]
    transform_attr = zone.attrs["spatial:transform"]
    a, _, c, _, e, f = transform_attr

    to_utm = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    xs, ys = to_utm.transform([west, east, west, east], [south, south, north, north])

    col0, col1 = int((min(xs) - c) / a), int((max(xs) - c) / a) + 1
    row0, row1 = int((max(ys) - f) / e), int((min(ys) - f) / e) + 1

    years = list(zone["time"][:])
    if args.year not in years:
        raise SystemExit(f"Year {args.year} not present. Store years: {years}")
    t = years.index(args.year)

    print(json.dumps({
        "event": "download_start",
        "year": args.year,
        "bands": args.bands,
        "utm_zone": zone_number,
        "crs": crs,
        "row_range": [row0, row1],
        "col_range": [col0, col1],
    }, indent=2))

    q = zone["embeddings"][t, 0:args.bands, row0:row1, col0:col1]
    if q.size == 0:
        raise SystemExit("Empty array slice returned for AOI.")
    if (q == -128).all():
        raise SystemExit(f"No OlmoEarth embeddings for this AOI in {args.year}: all pixels are nodata (-128).")

    # Official nonlinear dequantization. Never do arithmetic on q directly.
    values = np.where(q == -128, np.nan, q).astype("float32")
    values = (np.abs(values) / 127.5) ** 2.0 * np.sign(values)

    out_transform = Affine(a, 0, c + col0 * a, 0, e, f + row0 * e)
    with rasterio.open(
        output,
        "w",
        driver="GTiff",
        height=values.shape[1],
        width=values.shape[2],
        count=values.shape[0],
        dtype="float32",
        crs=crs,
        nodata=np.nan,
        compress="deflate",
        predictor=3,
        tiled=True,
    ) as dst:
        dst.write(values)
        dst.update_tags(
            source="OlmoEarth v1.3 global annual embeddings",
            source_url="https://source.coop/olmoearth/olmoearth-v1-3-embeddings",
            year=str(args.year),
            bands=str(args.bands),
            bbox_wgs84=",".join(map(str, args.bbox)),
            dequantization="(abs(q)/127.5)^2 * sign(q); q=-128 -> NaN",
        )

    finite_by_pixel = np.isfinite(values).all(axis=0)
    any_finite_by_pixel = np.isfinite(values).any(axis=0)
    summary = {
        "year": args.year,
        "bands": int(values.shape[0]),
        "height": int(values.shape[1]),
        "width": int(values.shape[2]),
        "crs": str(crs),
        "transform": list(out_transform)[:6],
        "bbox_wgs84": list(args.bbox),
        "utm_zone": zone_number,
        "all_bands_valid_pixel_fraction": float(finite_by_pixel.mean()),
        "any_band_valid_pixel_fraction": float(any_finite_by_pixel.mean()),
        "finite_min": float(np.nanmin(values)),
        "finite_max": float(np.nanmax(values)),
        "output": str(output),
        "sha256": sha256(output),
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"event": "export_complete", **summary}, indent=2))


if __name__ == "__main__":
    main()

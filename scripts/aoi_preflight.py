import json
from pathlib import Path
from pyproj import Transformer

bbox = [106.715, 10.785, 106.755, 10.815]
w, s, e, n = bbox
zone_w = int((w + 180) // 6) + 1
zone_e = int((e + 180) // 6) + 1
if zone_w != zone_e:
    raise SystemExit(f"AOI crosses UTM zones {zone_w} and {zone_e}")
crs = f"EPSG:326{zone_w:02d}"
tr = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
xs, ys = tr.transform([w,e,w,e], [s,s,n,n])
width_m = max(xs) - min(xs)
height_m = max(ys) - min(ys)
area_km2 = width_m * height_m / 1e6
result = {
    "bbox_wgs84": bbox,
    "utm_zone": zone_w,
    "expected_epsg": crs,
    "projected_x_range_m": [min(xs), max(xs)],
    "projected_y_range_m": [min(ys), max(ys)],
    "approx_width_m": width_m,
    "approx_height_m": height_m,
    "approx_area_km2": area_km2,
    "approx_10m_pixel_count": round(width_m / 10) * round(height_m / 10),
    "estimated_64d_float32_uncompressed_mb": (round(width_m / 10) * round(height_m / 10) * 64 * 4) / 1e6,
    "single_utm_zone": True
}
Path('logs').mkdir(exist_ok=True)
Path('logs/aoi_preflight.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))

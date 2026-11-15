import json
from pathlib import Path
import rasterio

REQUIRED = {
    "Gate B reliable land cover": ("outputs/reliable_landcover_2025.tif", 1),
    "Gate B reliable change": ("outputs/reliable_change_code_2017_2025.tif", 1),
    "Landsat moderate anomaly stack": ("data/shadeshift_gate_c3_landsat_moderate_anomalies.tif", 7),
    "Landsat guarded anomaly stack": ("data/shadeshift_gate_c3_landsat_guarded_anomalies.tif", 4),
    "C4 config": ("config/gate_c4_config.json", None),
    "C3 thermal validation provenance": ("notes/gate_c3_thermal_validation.json", None),
}

def main():
    checks = {}
    failures = []

    for name, (path_str, expected_bands) in REQUIRED.items():
        p = Path(path_str)
        item = {"path": path_str, "exists": p.exists()}
        if not p.exists():
            failures.append(f"Missing {name}: {path_str}")
            checks[name] = item
            continue

        if expected_bands is not None:
            try:
                with rasterio.open(p) as ds:
                    item.update({
                        "bands": ds.count,
                        "crs": ds.crs.to_string() if ds.crs else None,
                        "shape": [ds.height, ds.width],
                        "bounds": [ds.bounds.left, ds.bounds.bottom, ds.bounds.right, ds.bounds.top],
                    })
                    if ds.count != expected_bands:
                        failures.append(
                            f"{name}: expected {expected_bands} band(s), found {ds.count}"
                        )
                    if ds.crs is None or ds.crs.to_string() != "EPSG:32648":
                        failures.append(
                            f"{name}: expected EPSG:32648, found {ds.crs}"
                        )
            except Exception as e:
                failures.append(f"{name}: cannot open raster: {e}")

        checks[name] = item

    result = {
        "preflight_pass": not failures,
        "checks": checks,
        "failures": failures,
    }
    print(json.dumps(result, indent=2))
    if failures:
        raise SystemExit(2)

if __name__ == "__main__":
    main()

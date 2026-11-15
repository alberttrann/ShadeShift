import argparse, hashlib, json
from pathlib import Path
import rasterio
from rasterio.transform import Affine
from rasterio.warp import transform_bounds


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def repair(tif: Path, summary: Path):
    meta = json.loads(summary.read_text(encoding='utf-8'))
    expected = Affine(*meta['transform'])
    expected_crs = meta['crs']
    with rasterio.open(tif, 'r+') as ds:
        before = list(ds.transform)[:6]
        before_crs = ds.crs.to_string() if ds.crs else None
        ds.transform = expected
        if before_crs != expected_crs:
            ds.crs = expected_crs
        ds.update_tags(georef_repaired='true', georef_source_summary=str(summary))
    with rasterio.open(tif) as ds:
        after = list(ds.transform)[:6]
        bounds_utm = list(ds.bounds)
        bounds_wgs84 = list(transform_bounds(ds.crs, 'EPSG:4326', *ds.bounds, densify_pts=21))
    return {
        'tif': str(tif), 'before_transform': before, 'after_transform': after,
        'before_crs': before_crs, 'after_crs': expected_crs,
        'bounds_utm': bounds_utm, 'bounds_wgs84': bounds_wgs84,
        'sha256_after_repair': sha256(tif)
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root', default='.')
    ap.add_argument('--out', default='logs/gate_b_georef_repair.json')
    args=ap.parse_args()
    root=Path(args.root)
    pairs=[]
    for year in (2017,2025):
        tif=root/'data'/f'olmoearth_hcmc_{year}_64d.tif'
        summary=root/'data'/f'olmoearth_hcmc_{year}_64d.summary.json'
        if not tif.exists() or not summary.exists():
            raise SystemExit(f'Missing {tif} or {summary}')
        pairs.append(repair(tif, summary))
    out=root/args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({'georef_repair_pass': True, 'rasters': pairs}, indent=2), encoding='utf-8')
    print(json.dumps({'georef_repair_pass': True, 'rasters': pairs}, indent=2))

if __name__=='__main__': main()

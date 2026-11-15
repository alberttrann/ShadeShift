import argparse, json, math
from pathlib import Path
import rasterio
from rasterio.warp import transform_bounds

EXPECTED_BBOX=(106.715,10.785,106.755,10.815)

def inspect(path):
    with rasterio.open(path) as ds:
        wb=transform_bounds(ds.crs,'EPSG:4326',*ds.bounds,densify_pts=21)
        t=list(ds.transform)[:6]
        return {'path':str(path),'crs':ds.crs.to_string() if ds.crs else None,'transform':t,'bounds':list(ds.bounds),'bounds_wgs84':list(wb),'width':ds.width,'height':ds.height,'count':ds.count}

def bbox_close(actual, expected, tol=0.0015):
    return all(abs(a-e)<=tol for a,e in zip(actual,expected))

def non_identity(t):
    return not (abs(t[0]-1)<1e-12 and abs(t[1])<1e-12 and abs(t[2])<1e-12 and abs(t[3])<1e-12 and abs(t[4]-1)<1e-12 and abs(t[5])<1e-12)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',default='.'); ap.add_argument('--out',default='logs/gate_b_georef_qa.json'); args=ap.parse_args()
    root=Path(args.root)
    a=inspect(root/'data/olmoearth_hcmc_2017_64d.tif'); b=inspect(root/'data/olmoearth_hcmc_2025_64d.tif')
    checks={
      'crs_is_utm48': a['crs']=='EPSG:32648' and b['crs']=='EPSG:32648',
      'transforms_non_identity': non_identity(a['transform']) and non_identity(b['transform']),
      'pixel_size_10m_north_up': abs(a['transform'][0]-10)<1e-9 and abs(a['transform'][4]+10)<1e-9 and abs(b['transform'][0]-10)<1e-9 and abs(b['transform'][4]+10)<1e-9,
      'matching_grid': a['width']==b['width'] and a['height']==b['height'] and all(abs(x-y)<1e-9 for x,y in zip(a['transform'],b['transform'])),
      'bounds_match_requested_aoi': bbox_close(a['bounds_wgs84'], EXPECTED_BBOX) and bbox_close(b['bounds_wgs84'], EXPECTED_BBOX),
      'both_64_bands': a['count']==64 and b['count']==64,
    }
    result={'gate_b_preflight_georef_pass': all(checks.values()), 'checks':checks, '2017':a,'2025':b}
    out=root/args.out; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(result,indent=2)); raise SystemExit(0 if result['gate_b_preflight_georef_pass'] else 3)
if __name__=='__main__': main()

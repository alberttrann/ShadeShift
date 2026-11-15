from __future__ import annotations
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
failures=[]
checks={}

required=[
    ROOT/'apps/web/components/Dashboard.tsx',
    ROOT/'apps/web/components/MapView.tsx',
    ROOT/'apps/web/components/SurfaceLayers.tsx',
    ROOT/'apps/web/components/DetailPanel.tsx',
    ROOT/'apps/web/app/globals.css',
    ROOT/'apps/web/public/data/classifier/metadata.json',
]
for p in required:
    ok=p.exists() and p.stat().st_size>0
    checks[str(p.relative_to(ROOT))]={'exists':p.exists(),'bytes':p.stat().st_size if p.exists() else 0}
    if not ok: failures.append(f'missing required file: {p}')

meta_path=ROOT/'apps/web/public/data/classifier/metadata.json'
if meta_path.exists():
    meta=json.loads(meta_path.read_text(encoding='utf-8'))
    global_meta=meta.get('global')
    checks['metadata_version']=meta.get('version')
    checks['global_metadata_present']=bool(global_meta)
    if not global_meta:
        failures.append('classifier metadata has no global object')
    else:
        coords=global_meta.get('coordinates')
        checks['global_coordinates']=coords
        for key in ['landcover_url','veg_to_built_url']:
            url=global_meta.get(key)
            if not url:
                failures.append(f'global metadata missing {key}')
                continue
            path=ROOT/'apps/web/public'/url.lstrip('/')
            if not path.exists():
                failures.append(f'missing global raster asset: {path}')
                continue
            with Image.open(path) as im:
                checks[f'global_asset:{path.name}']={'size':list(im.size),'mode':im.mode}
                if im.mode!='RGBA': failures.append(f'{path.name} must be RGBA')

css=(ROOT/'apps/web/app/globals.css').read_text(encoding='utf-8') if (ROOT/'apps/web/app/globals.css').exists() else ''
map_src=(ROOT/'apps/web/components/MapView.tsx').read_text(encoding='utf-8') if (ROOT/'apps/web/components/MapView.tsx').exists() else ''
surface=(ROOT/'apps/web/components/SurfaceLayers.tsx').read_text(encoding='utf-8') if (ROOT/'apps/web/components/SurfaceLayers.tsx').exists() else ''
checks['readable_scale_override']='v2.1 readability + zoom resilience' in css
checks['fresh_global_metadata']='loadFreshClassifierMetadata' in map_src
checks['global_asset_probe']='assetIsReachable' in map_src
checks['surface_error_state']='surfaceError' in surface
for key in ['readable_scale_override','fresh_global_metadata','global_asset_probe','surface_error_state']:
    if not checks[key]: failures.append(f'code verification failed: {key}')

result={'status':'PASS' if not failures else 'FAIL','checks':checks,'failures':failures}
print(json.dumps(result,indent=2))
raise SystemExit(0 if not failures else 2)

import json
from pathlib import Path

qa_path = Path('logs/gate_a_raster_qa.json')
nasa_path = Path('logs/nasa_coverage.json')
status_path = Path('logs/gate_a_status.json')

if not qa_path.exists():
    raise SystemExit('Missing logs/gate_a_raster_qa.json; run qa_gate_a.py first.')
if not nasa_path.exists():
    raise SystemExit('Missing logs/nasa_coverage.json; fill from the Earth Engine probe first.')

qa = json.loads(qa_path.read_text(encoding='utf-8'))
nasa = json.loads(nasa_path.read_text(encoding='utf-8'))
status = json.loads(status_path.read_text(encoding='utf-8')) if status_path.exists() else {"gate":"A"}

eco = nasa.get('ecostress_usable_count')
mod = nasa.get('modis_usable_count')
nasa_pass = (isinstance(eco, int) and eco > 0) or (isinstance(mod, int) and mod > 0)
raster_pass = bool(qa.get('raster_qa_pass'))
final_pass = raster_pass and nasa_pass

status['pending_for_strict_pass'] = {
    '2025_64d_geotiff_exists': bool(qa.get('2025')),
    '2017_64d_geotiff_exists_or_logged_fallback': bool(qa.get('2017')),
    'raster_qa_pass': raster_pass,
    'nasa_aoi_usable_coverage_confirmed': nasa_pass,
}
status['gate_a_pass'] = final_pass
status['status'] = 'PASSED' if final_pass else 'NOT_PASSED_YET'
status['nasa_summary'] = nasa
status_path.write_text(json.dumps(status, indent=2), encoding='utf-8')
print(json.dumps(status, indent=2))
raise SystemExit(0 if final_pass else 4)

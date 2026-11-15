$ErrorActionPreference = "Stop"

Write-Host "[ShadeShift] Gate A environment bootstrap"
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python Launcher 'py' not found. Install Python 3.11 x64 first."
}

$ver = & py -3.11 -c "import sys; print('.'.join(map(str, sys.version_info[:3])))"
Write-Host "Python 3.11 detected: $ver"

if (-not (Test-Path ".venv")) {
    py -3.11 -m venv .venv
}
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-gate-a.txt

Write-Host "`n[1/4] Exporting 2025 OlmoEarth embeddings..."
python scripts/export_olmoearth.py --year 2025 --bands 64 --out-dir data

Write-Host "`n[2/4] Exporting 2017 OlmoEarth embeddings..."
python scripts/export_olmoearth.py --year 2017 --bands 64 --out-dir data

Write-Host "`n[3/4] Running raster QA..."
python scripts/qa_gate_a.py --y2017 data/olmoearth_hcmc_2017_64d.tif --y2025 data/olmoearth_hcmc_2025_64d.tif --out logs/gate_a_raster_qa.json

Write-Host "`n[4/4] Raster side complete. Now paste scripts/nasa_gate_a_ee.js into the Earth Engine Code Editor and record the printed usable-scene counts in logs/nasa_coverage.json."
Write-Host "Do NOT mark Gate A passed until raster QA passes AND at least one NASA collection reports usable AOI coverage."

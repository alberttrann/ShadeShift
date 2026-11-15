$ErrorActionPreference = "Stop"
Write-Host "[0/7] Installing Gate B dependencies..."
python -m pip install -r requirements-gate-b.txt

Write-Host "[1/7] Repairing missing GeoTIFF geotransforms from Gate A summaries..."
python scripts\repair_georef.py --root .
python scripts\qa_georef.py --root .
if (Test-Path "scripts\qa_gate_a.py") { python scripts\qa_gate_a.py --y2017 data\olmoearth_hcmc_2017_64d.tif --y2025 data\olmoearth_hcmc_2025_64d.tif --out logs\gate_a_raster_qa.json }

Write-Host "[2/7] LABELING REQUIRED"
Write-Host "Run scripts/gate_b_candidate_labels_ee.js in Earth Engine, export GeoJSON, review manually in QGIS, and save as labels/labels_reviewed.geojson."
Write-Host "Then resume with: .\scripts\resume_gate_b.ps1"

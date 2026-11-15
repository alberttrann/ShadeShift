$ErrorActionPreference = "Stop"
if (!(Test-Path "labels\labels_reviewed.geojson")) { throw "Missing labels\labels_reviewed.geojson. Finish manual review first." }
Write-Host "[3/7] Validating labels and constructing spatial train/val/test split..."
python scripts\validate_and_split_labels.py --labels labels\labels_reviewed.geojson
Write-Host "[4/7] Sampling 2025 OlmoEarth embeddings..."
python scripts\sample_embeddings.py
Write-Host "[5/7] Training baselines and evaluating held-out split..."
python scripts\train_classifier.py
Write-Host "[6/7] Predicting 2025 and 2017 class maps + unknown masks..."
python scripts\predict_classmaps.py --root . --threshold 0.60
Write-Host "[7/7] Checking manually inspected stable 2017 controls..."
python scripts\check_historical_controls.py
if (!(Test-Path "logs\gate_b_visual_review.json")) { Copy-Item logs\gate_b_visual_review.template.json logs\gate_b_visual_review.json }
Write-Host "Manual map inspection still required: edit logs\gate_b_visual_review.json after comparing the 2025 class map against imagery."
python scripts\finalize_gate_b.py

$ErrorActionPreference = "Stop"

if (!(Test-Path "labels\labels_reviewed.geojson")) {
    throw "Missing labels\labels_reviewed.geojson. Copy the frozen V2 label file first."
}

Write-Host "[V2 1/6] Validating frozen 3-class labels and spatial split..."
python scripts\validate_and_split_labels.py --labels labels\labels_reviewed.geojson

Write-Host "[V2 2/6] Sampling 2025 OlmoEarth embeddings..."
python scripts\sample_embeddings.py

Write-Host "[V2 3/6] Training Logistic + Random Forest baselines..."
python scripts\train_classifier.py

Write-Host "[V2 4/6] Predicting 2025 and 2017 class maps..."
python scripts\predict_classmaps.py --root . --threshold 0.60

Write-Host "[V2 5/6] Checking 2017 transfer controls..."
python scripts\check_historical_controls.py

if (!(Test-Path "logs\gate_b_visual_review.json")) {
    Copy-Item logs\gate_b_visual_review.template.json logs\gate_b_visual_review.json
}

Write-Host "[V2 6/6] Final status (manual whole-map visual review may still block PASS)..."
python scripts\finalize_gate_b.py

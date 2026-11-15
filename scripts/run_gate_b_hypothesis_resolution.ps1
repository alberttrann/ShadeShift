$ErrorActionPreference = "Stop"

Write-Host "[H1] Repeated spatial group holdouts..."
python scripts\audit_repeated_group_holdout.py

Write-Host "[H2] Label-permutation null test..."
python scripts\audit_label_permutation.py

Write-Host "[H3] Out-of-fold probability calibration..."
python scripts\audit_oof_calibration.py

Write-Host "[H4] Embedding-space support / OOD audit..."
python scripts\audit_embedding_support.py

Write-Host "[H5] Geographic quadrant holdouts..."
python scripts\audit_quadrant_holdout.py

Write-Host "[H6] Existing 5-fold group CV..."
python scripts\audit_spatial_cv.py

Write-Host "[H7] Pixel-wise 2017 -> 2025 transition audit..."
python scripts\audit_transitions.py

Write-Host "[H8] Targeted visual-review points..."
python scripts\make_targeted_visual_review.py

Write-Host "[H9] Consolidating automated hypothesis checks..."
python scripts\summarize_gate_b_hypotheses.py

Write-Host ""
Write-Host "Automated audits complete."
Write-Host "Next: inspect outputs\change_code_2017_2025.tif and labels\gate_b_targeted_visual_review.geojson in QGIS."

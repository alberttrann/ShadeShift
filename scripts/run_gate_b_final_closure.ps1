$ErrorActionPreference = "Stop"

Write-Host "[H1] Repeated spatial group holdouts..."
python scripts\audit_repeated_group_holdout.py

Write-Host "[H2] Label-permutation null test..."
python scripts\audit_label_permutation.py

Write-Host "[H3] Grouped OOF calibration..."
python scripts\audit_oof_calibration.py

Write-Host "[H4] Original 2025 embedding support audit..."
python scripts\audit_embedding_support.py

Write-Host "[H4b] Support audit for BOTH years + reliability masks..."
python scripts\audit_support_both_years.py

Write-Host "[H5] Geographic quadrant holdouts V2..."
python scripts\audit_quadrant_holdout_v2.py

Write-Host "[H6] 5-fold group CV..."
python scripts\audit_spatial_cv.py

Write-Host "[H7] Raw pixel transition audit..."
python scripts\audit_transitions.py

Write-Host "[H7b] Reliability-qualified transition audit..."
python scripts\audit_reliable_transitions.py

Write-Host "[H8] Targeted visual-review points..."
python scripts\make_targeted_visual_review.py

Write-Host "[H9] Original hypothesis summary..."
python scripts\summarize_gate_b_hypotheses.py

Write-Host ""
Write-Host "All automated Gate B closure audits completed."
Write-Host "Final human step: QGIS review of reliable maps, support masks, transitions, and targeted review points."

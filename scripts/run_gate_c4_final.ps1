$ErrorActionPreference="Stop"

Write-Host "[C4 1/3] Building final 500m planning grid..."
python scripts\build_gate_c4_planning_grid.py

Write-Host "[C4 2/3] Auditing priority sensitivity..."
python scripts\audit_gate_c4_priority_sensitivity.py

Write-Host "[C4 3/3] Finalizing Gate C..."
python scripts\finalize_gate_c.py

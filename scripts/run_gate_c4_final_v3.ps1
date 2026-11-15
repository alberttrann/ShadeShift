$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Run-PythonStep {
    param([string]$Label,[string]$Script)

    Write-Host $Label
    & python $Script

    if ($LASTEXITCODE -ne 0) {
        Write-Error "$Label failed with Python exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }
}

Run-PythonStep "[C4v3 0/4] Bootstrapping config/provenance..." "scripts\bootstrap_gate_c4.py"
Run-PythonStep "[C4v3 1/4] Preflight input validation..." "scripts\preflight_gate_c4.py"
Run-PythonStep "[C4v3 2/4] Rebuilding 500m grid with spatial-overlap guard..." "scripts\build_gate_c4_planning_grid.py"
Run-PythonStep "[C4v3 3/4] Re-running priority sensitivity..." "scripts\audit_gate_c4_priority_sensitivity.py"
Run-PythonStep "[C4v3 4/4] Finalizing Gate C..." "scripts\finalize_gate_c.py"

Write-Host ""
Write-Host "Gate C4 v3 spatial-fix pipeline completed successfully."

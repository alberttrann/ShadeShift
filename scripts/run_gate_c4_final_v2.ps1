$ErrorActionPreference = "Stop"

# Always run from the project root, regardless of where PowerShell was opened.
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Run-PythonStep {
    param(
        [string]$Label,
        [string]$Script
    )

    Write-Host $Label
    & python $Script

    if ($LASTEXITCODE -ne 0) {
        Write-Error "$Label failed with Python exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }
}

Run-PythonStep "[C4 0/4] Bootstrapping frozen C4 config/provenance..." "scripts\bootstrap_gate_c4.py"
Run-PythonStep "[C4 1/4] Preflight input validation..." "scripts\preflight_gate_c4.py"
Run-PythonStep "[C4 2/4] Building final 500m planning grid..." "scripts\build_gate_c4_planning_grid.py"
Run-PythonStep "[C4 3/4] Auditing priority sensitivity..." "scripts\audit_gate_c4_priority_sensitivity.py"
Run-PythonStep "[C4 4/4] Finalizing Gate C..." "scripts\finalize_gate_c.py"

Write-Host ""
Write-Host "Gate C4 v2 pipeline completed successfully."

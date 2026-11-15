$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "[C4.1] Running evidence-caveat resolution audit..."
& python "scripts\audit_and_enhance_gate_c4_evidence.py"

if ($LASTEXITCODE -ne 0) {
    Write-Error "C4.1 evidence audit failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "C4.1 evidence-caveat audit completed."

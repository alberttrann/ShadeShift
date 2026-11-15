param(
  [string]$RepoRoot = "D:\shadeshift_gate_a"
)

$ErrorActionPreference = "Stop"
$PatchRoot = $PSScriptRoot
$RepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)

function Copy-Patch {
  param([string]$RelativePath)
  $src = Join-Path $PatchRoot $RelativePath
  $dst = Join-Path $RepoRoot $RelativePath
  if (-not (Test-Path $src)) {
    throw "Patch file missing: $src"
  }
  New-Item -ItemType Directory -Force -Path (Split-Path $dst -Parent) | Out-Null
  Copy-Item -Force $src $dst
  Write-Host "  OK $RelativePath"
}

Write-Host "ShadeShift Railway deployment prep"
Write-Host "Target: $RepoRoot"
Write-Host ""

Copy-Patch ".gitignore"
Copy-Patch "product\apps\api\src\main.ts"
Copy-Patch "product\railway.api.toml"
Copy-Patch "product\railway.web.toml"
Copy-Patch "product\scripts\prepare-deployment-artifacts.ps1"
Copy-Patch "DEPLOY_RAILWAY.md"

Write-Host ""
Write-Host "Preparing frozen deployment artifacts..."
powershell -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "product\scripts\prepare-deployment-artifacts.ps1") -RepoRoot $RepoRoot
if ($LASTEXITCODE -ne 0) {
  throw "Deployment-artifact preparation failed."
}

Write-Host ""
Write-Host "Patch + artifacts ready."
Write-Host "Review with:"
Write-Host "  cd $RepoRoot"
Write-Host "  git status --short"

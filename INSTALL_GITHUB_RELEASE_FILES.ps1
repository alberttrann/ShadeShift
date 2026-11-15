param(
  [string]$RepoRoot = "D:\shadeshift_gate_a"
)

$ErrorActionPreference = "Stop"
$PackRoot = $PSScriptRoot

Copy-Item -Force (Join-Path $PackRoot "README.md") (Join-Path $RepoRoot "README.md")
Copy-Item -Force (Join-Path $PackRoot ".gitignore") (Join-Path $RepoRoot ".gitignore")
Copy-Item -Force (Join-Path $PackRoot "GITHUB_RELEASE_CHECKLIST.md") (Join-Path $RepoRoot "GITHUB_RELEASE_CHECKLIST.md")
Copy-Item -Force (Join-Path $PackRoot "PUSH_TO_GITHUB.ps1") (Join-Path $RepoRoot "PUSH_TO_GITHUB.ps1")
New-Item -ItemType Directory -Force -Path (Join-Path $RepoRoot "product") | Out-Null
Copy-Item -Force (Join-Path $PackRoot "product\README.md") (Join-Path $RepoRoot "product\README.md")

Write-Host "GitHub release metadata installed into $RepoRoot"
Write-Host ""
Write-Host "Review:"
Write-Host "  git status --short"
Write-Host ""
Write-Host "Then publish with:"
Write-Host "  .\PUSH_TO_GITHUB.ps1"

param(
  [string]$RepoRoot = "D:\shadeshift_gate_a"
)

$ErrorActionPreference = "Stop"
$RepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)
$ProductRoot = Join-Path $RepoRoot "product"
$ScienceData = Join-Path $RepoRoot "public\data"
$ApiData = Join-Path $ProductRoot "apps\api\data"
$ClassifierDir = Join-Path $ProductRoot "apps\web\public\data\classifier"

Write-Host "ShadeShift deployment-artifact preparation"
Write-Host "Repo: $RepoRoot"
Write-Host ""

if (-not (Test-Path $ProductRoot)) {
  throw "Missing product directory: $ProductRoot"
}

$requiredApi = @(
  "planning_cells_evidence_enhanced.geojson",
  "priority_top10_evidence_enhanced.json",
  "high_confidence_priority_top10.json"
)

Write-Host "[1/5] Verifying frozen science artifacts..."
foreach ($name in $requiredApi) {
  $src = Join-Path $ScienceData $name
  if (-not (Test-Path $src)) {
    throw @"
Missing frozen product artifact:
  $src

The deployment must use the final C4.1 outputs, not the older pre-spatial-fix files.
Run Gate C4.1 / verify public\data before deploying.
"@
  }
  Write-Host "  OK $name"
}

Write-Host "[2/5] Copying only frozen API artifacts into product/apps/api/data..."
New-Item -ItemType Directory -Force -Path $ApiData | Out-Null
foreach ($name in $requiredApi) {
  Copy-Item -Force (Join-Path $ScienceData $name) (Join-Path $ApiData $name)
}

Write-Host "[3/5] Ensuring global + selected-cell classifier visualization assets..."
$requiredClassifier = @(
  "metadata.json",
  "global_landcover_2025.png",
  "global_veg_to_built_2017_2025.png"
)

$classifierReady = $true
foreach ($name in $requiredClassifier) {
  if (-not (Test-Path (Join-Path $ClassifierDir $name))) {
    $classifierReady = $false
  }
}

$cellsDir = Join-Path $ClassifierDir "cells"
if (-not (Test-Path $cellsDir)) {
  $classifierReady = $false
} else {
  $cellPngCount = @(Get-ChildItem $cellsDir -File -Filter "*.png").Count
  if ($cellPngCount -lt 102) {
    $classifierReady = $false
  }
}

if (-not $classifierReady) {
  Write-Host "  classifier assets incomplete; regenerating..."
  Push-Location $ProductRoot
  python .\scripts\export_classifier_product_layers.py
  if ($LASTEXITCODE -ne 0) {
    Pop-Location
    throw "Classifier visualization export failed."
  }
  Pop-Location
} else {
  Write-Host "  existing classifier assets look complete."
}

Write-Host "[4/5] Verifying artifact contents..."

$geoPath = Join-Path $ApiData "planning_cells_evidence_enhanced.geojson"
$geo = Get-Content -Raw $geoPath | ConvertFrom-Json
if ($geo.type -ne "FeatureCollection") {
  throw "Enhanced planning artifact is not a GeoJSON FeatureCollection."
}

$total = @($geo.features).Count
$eligible = @($geo.features | Where-Object { $_.properties.eligible -eq $true })
$grades = @{}
foreach ($feature in $eligible) {
  $grade = [string]$feature.properties.evidence_grade
  if (-not $grades.ContainsKey($grade)) { $grades[$grade] = 0 }
  $grades[$grade] += 1
}

if ($total -ne 80) {
  throw "Expected 80 planning cells, found $total."
}
if ($eligible.Count -ne 51) {
  throw "Expected 51 eligible cells, found $($eligible.Count)."
}
if ($grades["A"] -ne 27 -or $grades["B"] -ne 22 -or $grades["C"] -ne 2) {
  throw "Unexpected evidence-grade distribution: $($grades | ConvertTo-Json -Compress)"
}

$metaPath = Join-Path $ClassifierDir "metadata.json"
if (-not (Test-Path $metaPath)) {
  throw "Classifier metadata is still missing after preparation."
}
$meta = Get-Content -Raw $metaPath | ConvertFrom-Json
if (-not $meta.global) {
  throw "Classifier metadata has no global section."
}

$cellPngCount = @(Get-ChildItem (Join-Path $ClassifierDir "cells") -File -Filter "*.png").Count
if ($cellPngCount -lt 102) {
  throw "Expected at least 102 selected-cell classifier PNGs, found $cellPngCount."
}

Write-Host "  Cells:    $total"
Write-Host "  Eligible: $($eligible.Count)"
Write-Host "  Grades:   A=$($grades["A"]) B=$($grades["B"]) C=$($grades["C"])"
Write-Host "  Cell PNGs: $cellPngCount"

Write-Host "[5/5] Deployment artifact preparation PASSED."
Write-Host ""
Write-Host "Next:"
Write-Host "  git add .gitignore product/apps/api/src/main.ts product/railway.api.toml product/railway.web.toml product/apps/api/data product/apps/web/public/data/classifier"
Write-Host "  git commit -m `"deploy: prepare Railway production services`""
Write-Host "  git push origin main"

param(
  [string]$BaseUrl = "http://localhost:4000/api/v1"
)

$ErrorActionPreference = "Stop"

function Assert-Equal {
  param($Actual, $Expected, [string]$Message)
  if ($Actual -ne $Expected) {
    throw "$Message | expected=$Expected actual=$Actual"
  }
}

function Assert-Approx {
  param(
    [double]$Actual,
    [double]$Expected,
    [double]$Tolerance,
    [string]$Message
  )
  if ([Math]::Abs($Actual - $Expected) -gt $Tolerance) {
    throw "$Message | expected=$Expected actual=$Actual tolerance=$Tolerance"
  }
}

function Get-Json {
  param([string]$Path)

  # Use raw response text + ConvertFrom-Json instead of Invoke-RestMethod.
  # Windows PowerShell 5.1 can wrap a top-level JSON array in a way that makes
  # @(...).Count report 1 even when the response contains 10 objects.
  $response = Invoke-WebRequest `
    -Uri "$BaseUrl$Path" `
    -Method Get `
    -UseBasicParsing

  return ($response.Content | ConvertFrom-Json)
}

function Get-JsonArray {
  param([string]$Path)

  $value = Get-Json $Path

  # ConvertFrom-Json gives us a true Object[] for a JSON array.
  # Force collection semantics for the single-element edge case too.
  return @($value)
}

function Assert-HttpStatus {
  param(
    [string]$Path,
    [int]$ExpectedStatus
  )

  try {
    Invoke-WebRequest `
      -Uri "$BaseUrl$Path" `
      -Method Get `
      -UseBasicParsing `
      -ErrorAction Stop | Out-Null

    throw "Expected HTTP $ExpectedStatus for $Path but request succeeded."
  }
  catch {
    $status = $null

    if ($_.Exception.Response) {
      try {
        $status = [int]$_.Exception.Response.StatusCode
      }
      catch {
        try {
          $status = $_.Exception.Response.StatusCode.value__
        }
        catch {}
      }
    }

    if ($status -ne $ExpectedStatus) {
      throw "Expected HTTP $ExpectedStatus for $Path, got $status"
    }
  }
}

Write-Host ""
Write-Host "ShadeShift D1 API smoke test v2"
Write-Host "Base URL: $BaseUrl"
Write-Host ""

Write-Host "[1/10] Health..."
$health = Get-Json "/health"
Assert-Equal $health.status "ok" "Health status mismatch"
Assert-Equal $health.cellsLoaded 80 "Health cellsLoaded mismatch"
Assert-Equal $health.enhanced $true "Enhanced artifact flag must be true"
Write-Host "  PASS"

Write-Host "[2/10] Metadata..."
$meta = Get-Json "/meta"
Assert-Equal $meta.totalCells 80 "Meta totalCells mismatch"
Assert-Equal $meta.eligibleCells 51 "Meta eligibleCells mismatch"
Assert-Equal $meta.evidenceGrades.A 27 "Grade A count mismatch"
Assert-Equal $meta.evidenceGrades.B 22 "Grade B count mismatch"
Assert-Equal $meta.evidenceGrades.C 2 "Grade C count mismatch"

if ($meta.semantics.priority -notmatch "not a risk probability") {
  throw "Priority semantics lost the non-probability warning."
}
Write-Host "  PASS"

Write-Host "[3/10] Eligible-cell GeoJSON..."
$cells = Get-Json "/cells?eligible=true"
Assert-Equal $cells.type "FeatureCollection" "Cells response is not FeatureCollection"
Assert-Equal @($cells.features).Count 51 "Eligible-cell count mismatch"
Write-Host "  PASS"

Write-Host "[4/10] Grade-A GeoJSON filter..."
$gradeA = Get-Json "/cells?eligible=true&evidenceGrade=A"
Assert-Equal @($gradeA.features).Count 27 "Grade-A filter count mismatch"
foreach ($feature in @($gradeA.features)) {
  Assert-Equal $feature.properties.evidenceGrade "A" "Non-A cell leaked into Grade-A filter"
}
Write-Host "  PASS"

Write-Host "[5/10] C025 detail contract..."
$c025 = Get-Json "/cells/C025"
Assert-Equal $c025.cellId "C025" "C025 ID mismatch"
Assert-Equal $c025.priority.rank 1 "C025 rank mismatch"
Assert-Approx $c025.priority.score 0.9455345331487462 1e-9 "C025 priority score mismatch"
Assert-Approx $c025.heat.score 0.9272727272727272 1e-9 "C025 heat score mismatch"
Assert-Equal $c025.heat.sceneCount 5 "C025 heat scene count mismatch"
Assert-Equal $c025.evidence.grade "A" "C025 evidence grade mismatch"
Assert-Equal $c025.evidence.temporalStrength "strong" "C025 temporal strength mismatch"
Assert-Equal $c025.evidence.qaStrength "strong" "C025 QA strength mismatch"
Assert-Equal $c025.evidence.spatialStrength "full" "C025 spatial strength mismatch"
Assert-Equal @($c025.evidence.caveats).Count 0 "C025 should have no caveats"
Write-Host "  PASS"

Write-Host "[6/10] Standard priority Top-10..."
$top = Get-JsonArray "/priorities/top?limit=10&strongEvidenceOnly=false"
Write-Host "  Returned records:" $top.Count
Assert-Equal $top.Count 10 "Default Top-10 length mismatch"
Assert-Equal $top[0].cellId "C025" "Default Top-10 first cell mismatch"
Assert-Equal $top[0].priorityRank 1 "Default Top-10 first rank mismatch"
Assert-Equal $top[1].cellId "C051" "Default Top-10 second cell mismatch"
Write-Host "  PASS"

Write-Host "[7/10] Strong-evidence Top-10..."
$strong = Get-JsonArray "/priorities/top?limit=10&strongEvidenceOnly=true"
Write-Host "  Returned records:" $strong.Count
Assert-Equal $strong.Count 10 "Strong Top-10 length mismatch"
Assert-Equal $strong[0].cellId "C025" "Strong Top-10 first cell mismatch"
Assert-Equal $strong[0].highConfidencePriorityRank 1 "Strong Top-10 rank mismatch"
foreach ($item in $strong) {
  Assert-Equal $item.evidence.grade "A" "Non-A cell leaked into strong-evidence shortlist"
}
Write-Host "  PASS"

Write-Host "[8/10] Methodology contract..."
$method = Get-Json "/methodology"
if ($method.priorityFormula -notmatch "0.60" -or $method.priorityFormula -notmatch "0.40") {
  throw "Methodology priority formula mismatch."
}
if ($method.ecostressRole -notmatch "context") {
  throw "ECOSTRESS role is not described as contextual."
}
Write-Host "  PASS"

Write-Host "[9/10] Layer metadata..."
$layers = Get-JsonArray "/layers"
Assert-Equal $layers.Count 4 "Expected exactly four product map modes"
$layerIds = @($layers | ForEach-Object { $_.id })
foreach ($required in @("priority", "heat", "greening", "evidence")) {
  if ($required -notin $layerIds) {
    throw "Missing map layer definition: $required"
  }
}
Write-Host "  PASS"

Write-Host "[10/10] Error behavior..."
Assert-HttpStatus "/cells/NO_SUCH_CELL" 404
Assert-HttpStatus "/cells?bbox=broken" 400
Write-Host "  PASS"

Write-Host ""
Write-Host "==============================================="
Write-Host "SHADE SHIFT D1 API CONTRACT: PASS"
Write-Host "==============================================="
Write-Host ""
Write-Host "Validated:"
Write-Host "  - enhanced C4.1 artifacts are loaded"
Write-Host "  - 80 total / 51 eligible"
Write-Host "  - evidence grades 27 A / 22 B / 2 C"
Write-Host "  - C025 scientific values survive DTO mapping"
Write-Host "  - normal and strong-evidence Top-10 arrays contain 10 records"
Write-Host "  - methodology preserves scientific semantics"
Write-Host "  - bad requests fail correctly"

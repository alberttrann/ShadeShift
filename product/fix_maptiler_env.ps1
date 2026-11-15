$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

Write-Host "[1/3] Syncing root .env into the Next.js app root..."
node .\scripts\sync-web-env.mjs
if ($LASTEXITCODE -ne 0) {
  throw "Frontend env sync failed."
}

Write-Host "[2/3] Checking generated apps\web\.env.local..."
if (-not (Test-Path ".\apps\web\.env.local")) {
  throw "apps\web\.env.local was not created."
}

$Generated = Get-Content ".\apps\web\.env.local" -Raw

if ($Generated -match "NEXT_PUBLIC_MAPTILER_API_KEY=\s*$") {
  Write-Warning "MapTiler key is still blank in apps\web\.env.local."
} else {
  Write-Host "  MapTiler browser key: PRESENT (hidden)"
}

if ($Generated -match "NEXT_PUBLIC_API_BASE_URL=http://localhost:4000/api/v1") {
  Write-Host "  API base URL: PRESENT"
} else {
  Write-Warning "API base URL is missing or different."
}

Write-Host "[3/3] Done."
Write-Host ""
Write-Host "IMPORTANT: stop the current dev server with Ctrl+C, then run:"
Write-Host "  npm run dev"
Write-Host ""
Write-Host "NEXT_PUBLIC_* values are bundled by Next.js, so a restart is required."

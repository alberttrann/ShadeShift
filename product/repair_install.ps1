$ErrorActionPreference = "Stop"

$ProductRoot = $PSScriptRoot
Set-Location $ProductRoot

Write-Host "[1/5] Cleaning failed/partial npm installation..."
if (Test-Path "node_modules") {
    Remove-Item "node_modules" -Recurse -Force
}
if (Test-Path "package-lock.json") {
    Remove-Item "package-lock.json" -Force
}

# Clean nested node_modules if npm created any before failing.
Get-ChildItem -Path "apps","packages" -Directory -Recurse -Filter "node_modules" -ErrorAction SilentlyContinue |
    ForEach-Object {
        Remove-Item $_.FullName -Recurse -Force
    }

Write-Host "[2/5] Printing runtime versions..."
node --version
npm --version

Write-Host "[3/5] Installing dependencies..."
npm install
if ($LASTEXITCODE -ne 0) {
    throw "npm install failed with exit code $LASTEXITCODE"
}

Write-Host "[4/5] Running data preflight..."
npm run preflight:data
if ($LASTEXITCODE -ne 0) {
    throw "data preflight failed with exit code $LASTEXITCODE"
}

Write-Host "[5/5] Building shared contracts..."
npm run build:contracts
if ($LASTEXITCODE -ne 0) {
    throw "contract build failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "ShadeShift product repair/install completed successfully."
Write-Host "Next run:"
Write-Host "  npm run dev"

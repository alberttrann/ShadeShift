param(
  [string]$RepoRoot = "D:\shadeshift_gate_a",
  [string]$RemoteUrl = "https://github.com/alberttrann/ShadeShift.git",
  [string]$Branch = "main",
  [string]$Message = "feat: publish ShadeShift local experiment"
)

$ErrorActionPreference = "Stop"

# PowerShell 7 can turn expected native non-zero exit codes into terminating
# errors when this preference is enabled. We handle git exit codes ourselves.
if (Get-Variable PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
  $PSNativeCommandUseErrorActionPreference = $false
}

$RepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)

function Invoke-Git {
  param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$GitArgs
  )

  & git @GitArgs
  if ($LASTEXITCODE -ne 0) {
    throw "git $($GitArgs -join ' ') failed with exit code $LASTEXITCODE."
  }
}

function Get-GitOutput {
  param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$GitArgs
  )

  $output = & git @GitArgs
  if ($LASTEXITCODE -ne 0) {
    throw "git $($GitArgs -join ' ') failed with exit code $LASTEXITCODE."
  }

  return @($output)
}

Write-Host "ShadeShift GitHub release"
Write-Host "Root:   $RepoRoot"
Write-Host "Remote: $RemoteUrl"
Write-Host ""

if (-not (Test-Path $RepoRoot)) {
  throw "Repository root not found: $RepoRoot"
}

Set-Location $RepoRoot

# ---------------------------------------------------------------------------
# 1. Repository
# ---------------------------------------------------------------------------
if (-not (Test-Path ".git")) {
  Write-Host "[1/10] Initializing Git repository..."
  Invoke-Git init
} else {
  Write-Host "[1/10] Existing Git repository detected."
}

# ---------------------------------------------------------------------------
# 2. Origin
# ---------------------------------------------------------------------------
Write-Host "[2/10] Checking origin..."
$remotes = @(Get-GitOutput remote)

if ($remotes -contains "origin") {
  $originLines = @(Get-GitOutput remote get-url origin)
  $origin = ($originLines | Select-Object -First 1).Trim()

  if ($origin -ne $RemoteUrl) {
    throw "Existing origin is '$origin', expected '$RemoteUrl'. Refusing to rewrite it automatically."
  }

  Write-Host "  origin already correct."
} else {
  Invoke-Git remote add origin $RemoteUrl
  Write-Host "  added origin."
}

# ---------------------------------------------------------------------------
# 3. Branch name
# ---------------------------------------------------------------------------
Write-Host "[3/10] Normalizing local branch to '$Branch'..."
Invoke-Git branch -M $Branch

# ---------------------------------------------------------------------------
# 4. Tracked-secret check
#
# IMPORTANT: do not use `git ls-files --error-unmatch`. "Not tracked" is the
# healthy case and should not require a non-zero probe.
# ---------------------------------------------------------------------------
Write-Host "[4/10] Checking tracked secrets..."

$badTracked = @(
  ".env",
  "product/.env",
  "product/apps/web/.env.local"
)

foreach ($bad in $badTracked) {
  $matches = @(Get-GitOutput ls-files --cached -- $bad)
  if ($matches.Count -gt 0) {
    throw @"
Secret/local file is already tracked: $bad

Remove it from the index while keeping the local file:
  git rm --cached -- "$bad"

Then run .\PUSH_TO_GITHUB.ps1 again.
"@
  }
}

Write-Host "  no tracked secret env files found."

# ---------------------------------------------------------------------------
# 5. Stage using .gitignore
# ---------------------------------------------------------------------------
Write-Host "[5/10] Staging repository..."
Invoke-Git add -A

$staged = @(Get-GitOutput diff --cached --name-only)
$staged = @($staged | Where-Object { $_ -and $_.Trim() })

if ($staged.Count -eq 0) {
  Write-Host ""
  Write-Host "Nothing new to commit."
  Write-Host "Repository may already be up to date."
  exit 0
}

# ---------------------------------------------------------------------------
# 6. Staged-file audit
# ---------------------------------------------------------------------------
Write-Host "[6/10] Auditing staged files..."

$forbidden = @(
  $staged | Where-Object {
    $_ -match '\.(tif|tiff|pth|pt|ckpt|mbtiles)$' -or
    $_ -match '(^|/)\.env$' -or
    $_ -match 'apps/web/\.env\.local$' -or
    $_ -match '(^|/)node_modules/' -or
    $_ -match '(^|/)\.venv/'
  }
)

if ($forbidden.Count -gt 0) {
  Write-Host ""
  Write-Host "Refusing to commit forbidden files:"
  $forbidden | ForEach-Object { Write-Host "  $_" }
  throw "Remove these files from the Git index before publishing."
}

$large = @()
foreach ($f in $staged) {
  if (Test-Path -LiteralPath $f) {
    $item = Get-Item -LiteralPath $f
    if (-not $item.PSIsContainer -and $item.Length -gt 50MB) {
      $large += "$f ($([math]::Round($item.Length / 1MB, 1)) MiB)"
    }
  }
}

if ($large.Count -gt 0) {
  Write-Host ""
  Write-Host "Refusing staged files larger than 50 MiB:"
  $large | ForEach-Object { Write-Host "  $_" }
  throw "Move large science artifacts out of Git before publishing."
}

Write-Host "  staged-file audit passed."

# ---------------------------------------------------------------------------
# 7. Show exact staged summary
# ---------------------------------------------------------------------------
Write-Host "[7/10] Staged summary:"
Invoke-Git status --short

# ---------------------------------------------------------------------------
# 8. Git identity
#
# `git config --list` succeeds even if name/email are absent, so there is no
# expected-failure probe here either.
# ---------------------------------------------------------------------------
Write-Host "[8/10] Checking Git identity..."

$configLines = @(Get-GitOutput config --list)
$nameLine = $configLines |
  Where-Object { $_ -like "user.name=*" } |
  Select-Object -Last 1
$emailLine = $configLines |
  Where-Object { $_ -like "user.email=*" } |
  Select-Object -Last 1

$name = if ($nameLine) { $nameLine.Substring("user.name=".Length) } else { "" }
$email = if ($emailLine) { $emailLine.Substring("user.email=".Length) } else { "" }

if ([string]::IsNullOrWhiteSpace($name) -or
    [string]::IsNullOrWhiteSpace($email)) {
  throw @"
Git user.name / user.email are not configured.

Configure them once, for example:
  git config --global user.name "Your Name"
  git config --global user.email "your-email@example.com"

Then run .\PUSH_TO_GITHUB.ps1 again.
"@
}

Write-Host "  $name <$email>"

# ---------------------------------------------------------------------------
# 9. Query remote history
#
# `git ls-remote --heads` exits 0 even if the requested branch does not exist.
# ---------------------------------------------------------------------------
Write-Host "[9/10] Checking remote '$Branch' history..."

$remoteHead = @(& git ls-remote --heads origin $Branch)
if ($LASTEXITCODE -ne 0) {
  throw "Could not query origin. Check GitHub authentication/network access."
}
$remoteHead = @($remoteHead | Where-Object { $_ -and $_.Trim() })
$remoteExists = $remoteHead.Count -gt 0

if ($remoteExists) {
  Write-Host "  origin/$Branch exists; fetching before commit..."
  Invoke-Git fetch origin $Branch
} else {
  Write-Host "  origin/$Branch is empty / absent."
}

# ---------------------------------------------------------------------------
# 10. Commit, verify ancestry, and push
# ---------------------------------------------------------------------------
Write-Host "[10/10] Committing and pushing..."

Invoke-Git commit -m $Message

if ($remoteExists) {
  # `rev-list --left-right --count A...B` succeeds for both related and
  # unrelated histories. The left count is the number of remote commits that
  # are not in local HEAD. Any positive left count means a normal push would
  # discard or bypass remote history, so stop instead of force-pushing.
  $counts = @(Get-GitOutput rev-list --left-right --count "origin/$Branch...HEAD")
  $parts = ($counts | Select-Object -First 1) -split '\s+'

  if ($parts.Count -lt 2) {
    throw "Could not parse Git ancestry comparison: $($counts -join ' ')"
  }

  $remoteOnly = [int]$parts[0]
  $localOnly = [int]$parts[1]

  Write-Host "  ancestry: remote-only=$remoteOnly local-only=$localOnly"

  if ($remoteOnly -gt 0) {
    throw @"
origin/$Branch contains commits that are not in this local branch.

Your local commit was created, but NO PUSH was attempted and NO FORCE PUSH
was attempted.

Inspect safely:
  git log --oneline --graph --decorate --all -30

Then merge/rebase the remote history deliberately before pushing.
"@
  }
}

Invoke-Git push -u origin $Branch

Write-Host ""
Write-Host "ShadeShift pushed successfully."
Write-Host "https://github.com/alberttrann/ShadeShift"

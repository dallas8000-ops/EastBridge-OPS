# Start EastBridge in this terminal — no extra PowerShell windows.
# Usage: .\scripts\dev.ps1   or   npm run dev

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Frontend = Join-Path $RepoRoot "frontend"

if (-not (Test-Path $VenvPython)) {
    Write-Error @"
Virtual env not found. First-time setup:
  cd `"$RepoRoot`"
  python -m venv .venv
  .\.venv\Scripts\pip install -r backend\requirements.txt
  npm install
  cd backend && ..\.venv\Scripts\python manage.py migrate && ..\.venv\Scripts\python manage.py seed_data
"@
    exit 1
}

if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
    Write-Host "Installing frontend dependencies..."
    Push-Location $Frontend
    npm install
    Pop-Location
}

if (-not (Test-Path (Join-Path $RepoRoot "node_modules\concurrently"))) {
    Write-Host "Installing dev launcher dependencies..."
    Push-Location $RepoRoot
    npm install
    Pop-Location
}

Write-Host "Starting EastBridge (API + UI in this window). Press Ctrl+C to stop."
Write-Host ""

Set-Location $RepoRoot
npm run dev:stack

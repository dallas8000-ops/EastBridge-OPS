# Export the full app data image into backend/fixtures/ for GitHub zip downloads.
# Usage: .\scripts\export-fixtures.ps1 [-Check]

param(
    [switch]$Check
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Error "Create .venv first: python -m venv .venv && .\.venv\Scripts\pip install -r backend\requirements.txt"
}

$env:DATABASE_URL = ""
$env:EMBEDDING_PROVIDER = "hash"

Push-Location backend
try {
    if ($Check) {
        & $Python manage.py export_app_data --check
    } else {
        & $Python manage.py export_app_data --refresh
    }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
    Pop-Location
}

if (-not $Check) {
    Write-Host ""
    Write-Host "Fixture files updated under backend/fixtures/" -ForegroundColor Green
    Write-Host "Commit and push so GitHub zip downloads include the full app image:"
    Write-Host "  git add backend/fixtures/"
    Write-Host "  git commit -m `"Update app data fixtures for zip download`""
    Write-Host "  git push"
}

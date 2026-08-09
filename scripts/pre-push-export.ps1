# Called by .githooks/pre-push — export fixtures and block push if they were not committed.
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Host "pre-push: skipping fixture export (.venv missing)" -ForegroundColor Yellow
    exit 0
}

$env:DATABASE_URL = ""
$env:EMBEDDING_PROVIDER = "hash"

Push-Location backend
& $Python manage.py export_app_data --refresh
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Pop-Location

$dirty = git status --porcelain -- backend/fixtures/
if ($dirty) {
    git add backend/fixtures/
    Write-Host ""
    Write-Host "pre-push: fixture files were updated to match the app image." -ForegroundColor Yellow
    Write-Host "They are staged. Commit them, then push again:"
    Write-Host "  git commit -m `"Update app data fixtures for zip download`""
    Write-Host "  git push"
    exit 1
}

exit 0

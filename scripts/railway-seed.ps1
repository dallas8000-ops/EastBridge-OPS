# Run full production seed on Railway (EastBridge-OPS service).
# Usage: .\scripts\railway-seed.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "Linking EastBridge-OPS on Railway (hearty-enjoyment / production)..."
railway link -p hearty-enjoyment -e production -s EastBridge-OPS

$steps = @(
    @{ Name = "seed_data"; Cmd = "python manage.py seed_data" },
    @{ Name = "seed_demo_org"; Cmd = "python manage.py seed_demo_org" },
    @{ Name = "ingest"; Cmd = "python manage.py ingest --target all" },
    @{ Name = "trade"; Cmd = "python manage.py sync_trade_procedures --offline" },
    @{ Name = "embed"; Cmd = "python manage.py embed_evidence --force" },
    @{ Name = "verify"; Cmd = "python manage.py verify_data" }
)

foreach ($step in $steps) {
    Write-Host ""
    Write-Host "==> $($step.Name)" -ForegroundColor Cyan
    railway run $($step.Cmd)
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Step $($step.Name) failed."
    }
}

Write-Host ""
Write-Host "Seed complete. Create a production login if needed:" -ForegroundColor Green
Write-Host "  railway run python manage.py createsuperuser"
Write-Host "App: https://eastbridge-ops-production.up.railway.app/"

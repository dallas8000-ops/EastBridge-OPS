# Start EastBridge Ops Intelligence (backend :8888 + frontend :5173 + open browser)
# Run from repo root: .\start.ps1   or   npm run dev   or   .\scripts\dev.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $RepoRoot "backend"
$Frontend = Join-Path $RepoRoot "frontend"
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$PsExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$ApiUrl = "http://127.0.0.1:8888/api/v1/health/"
$UiUrl = "http://127.0.0.1:5173/"

function Wait-HttpOk {
    param([string]$Url, [int]$Seconds = 60)
    for ($i = 0; $i -lt $Seconds; $i++) {
        try {
            $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 400) { return $true }
        } catch {}
        Start-Sleep -Seconds 1
    }
    return $false
}

if (-not (Test-Path $VenvPython)) {
    Write-Error @"
Virtual env not found at $VenvPython

First-time setup:
  cd `"$RepoRoot`"
  python -m venv .venv
  .\.venv\Scripts\pip install -r backend\requirements.txt
  cd backend
  ..\.venv\Scripts\python manage.py migrate
  ..\.venv\Scripts\python manage.py seed_data
  ..\.venv\Scripts\python manage.py seed_demo_org
"@
    exit 1
}

if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
    Write-Host "Installing frontend dependencies..."
    Push-Location $Frontend
    npm install
    Pop-Location
}

if (-not (Wait-HttpOk -Url $ApiUrl -Seconds 3)) {
    Write-Host "Starting Django API on http://127.0.0.1:8888 ..."
    Start-Process -FilePath $PsExe -WorkingDirectory $Backend -ArgumentList @(
        "-NoExit",
        "-Command",
        "& '$VenvPython' manage.py runserver 127.0.0.1:8888"
    )
    if (-not (Wait-HttpOk -Url $ApiUrl)) {
        Write-Error "Backend did not become healthy at $ApiUrl"
        exit 1
    }
} else {
    Write-Host "Backend already running at http://127.0.0.1:8888"
}

if (-not (Wait-HttpOk -Url $UiUrl -Seconds 3)) {
    Write-Host "Starting Vite UI on http://127.0.0.1:5173 ..."
    $viteCmd = "`$env:VITE_API_PROXY='http://127.0.0.1:8888'; npm run dev -- --port 5173 --host 127.0.0.1"
    Start-Process -FilePath $PsExe -WorkingDirectory $Frontend -ArgumentList @(
        "-NoExit",
        "-Command",
        $viteCmd
    )
    if (-not (Wait-HttpOk -Url $UiUrl)) {
        Write-Error "Frontend did not become ready at $UiUrl"
        exit 1
    }
} else {
    Write-Host "Frontend already running at $UiUrl"
}

Start-Process $UiUrl

Write-Host ""
Write-Host "EastBridge is ready"
Write-Host "  UI:  $UiUrl"
Write-Host "  API: http://127.0.0.1:8888/api/v1/health/"
Write-Host "  Login: demo / demo12345"
Write-Host ""
Write-Host "Close the Django and Vite PowerShell windows to stop the app."

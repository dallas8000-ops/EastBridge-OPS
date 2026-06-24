# Run API smoke test (backend must be optional — uses Django test client directly)
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root "..\.venv\Scripts\python.exe"
$Backend = Join-Path $Root "..\backend"

& $Python (Join-Path $Backend "smoke_test.py")
exit $LASTEXITCODE

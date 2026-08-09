# Point this repo at .githooks/ so pre-push refreshes fixture exports.
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

git config core.hooksPath .githooks
Write-Host "Git hooks enabled (.githooks/pre-push will refresh fixtures before push)." -ForegroundColor Green
Write-Host "Run once after clone: .\scripts\install-git-hooks.ps1"

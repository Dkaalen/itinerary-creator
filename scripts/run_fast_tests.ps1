$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "Running fast safety tests..." -ForegroundColor Cyan
python .\scripts\run_test_group.py fast

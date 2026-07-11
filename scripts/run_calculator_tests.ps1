$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "Running calculator tests..." -ForegroundColor Cyan
python .\scripts\run_test_group.py calculator @args

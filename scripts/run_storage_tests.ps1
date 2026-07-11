$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "Running storage tests..." -ForegroundColor Cyan
python .\scripts\run_test_group.py storage @args

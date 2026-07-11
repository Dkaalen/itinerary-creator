$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "Running architecture/source-of-truth tests..." -ForegroundColor Cyan
python .\scripts\run_test_group.py architecture @args

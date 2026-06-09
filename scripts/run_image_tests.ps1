$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "Running image-bank and image-matching tests..." -ForegroundColor Cyan
python .\scripts\run_test_group.py images

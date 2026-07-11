$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "Running full test suite in progress-tracked groups..." -ForegroundColor Cyan
python .\scripts\run_test_group.py full @args

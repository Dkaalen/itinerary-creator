$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "Running editor/draft-state tests..." -ForegroundColor Cyan
python .\scripts\run_test_group.py editor @args

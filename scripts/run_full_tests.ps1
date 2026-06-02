$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "Running full test suite..." -ForegroundColor Cyan
python -m pytest -q

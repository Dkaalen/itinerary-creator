$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "Running PDF/rendering tests..." -ForegroundColor Cyan
python -m pytest -q -m "pdf"

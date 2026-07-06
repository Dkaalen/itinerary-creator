$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "Running quick health check..." -ForegroundColor Cyan
python .\scripts\run_health_check.py

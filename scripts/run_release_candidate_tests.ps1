$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "Running release candidate validation..." -ForegroundColor Cyan
python .\scripts\run_release_candidate.py @args

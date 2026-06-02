$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "Running fast safety tests..." -ForegroundColor Cyan
python -m pytest -q `
  tests/test_time_text_helpers.py `
  tests/test_date_formatting.py `
  tests/test_date_resolver.py `
  tests/test_render_cache.py `
  tests/test_commercial_status_helpers.py `
  tests/test_normalizer_context_architecture.py `
  tests/test_regressions_parser_normalizer.py `
  tests/test_stress_logic_followups.py

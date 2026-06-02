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
  tests/test_transport_model_architecture.py `
  tests/test_regressions_parser_normalizer.py `
  tests/test_stress_logic_followups.py `
  tests/test_itinerary_health_report.py `
  tests/test_content_validator_scoping.py `
  tests/test_fixture_quality_polish.py `
  tests/test_nordic_quality_sample.py `
  tests/test_compound_experience_transport_timing.py `
  tests/test_accommodation_stress_fixtures.py `
  tests/test_activity_compound_stress_fixtures.py `
  tests/test_leisure_arrival_metadata_cleanup.py

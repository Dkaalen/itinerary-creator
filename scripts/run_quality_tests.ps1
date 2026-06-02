$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "Running medium quality tests..." -ForegroundColor Cyan
python -m pytest -q `
  tests/test_accommodation_wording.py `
  tests/test_content_classification_priority.py `
  tests/test_canonical_block_renderers.py `
  tests/test_canonical_boundary.py `
  tests/test_inclusions_preview_accommodation_transport_followups.py `
  tests/test_inclusion_exclusion_architecture.py `
  tests/test_quality_gate_architecture.py `
  tests/test_premium_optional_output.py `
  tests/test_regressions_content_basics.py `
  tests/test_regressions_content_generation.py `
  tests/test_regressions_transport_cruise.py `
  tests/test_finland_transport_regressions.py `
  tests/test_regressions_pdf_inclusions.py

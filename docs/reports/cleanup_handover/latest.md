# Cleanup Handover Report

Generated after Patches 124-128 cleanup pass.

## What changed

### Patch 124: Parser/generation ownership audit

Added `scripts/parser_generation_ownership_audit.py` plus handover reports:

* `docs/reports/parser_generation_ownership/latest.md`
* `docs/reports/parser_generation_ownership/latest.json`

Current result: `116` review signals. No behavior was changed. The highest-priority finding is normalizer/parser modules still importing generation-layer helpers in several places. Treat these as future refactor targets, not deletion candidates.

### Patch 125: Real-output QA maintenance

Moved reusable real-output QA logic under `scripts/real_output_qa/`:

* `selection.py` — fixture selection and review building
* `markdown.py` — readable markdown report formatting
* `score_reports.py` — compact JSON score report assembly
* `random_checks.py` — seeded random quality-check report assembly
* `indexing.py` — QA index markdown/json generation

Kept old CLI script names as compatibility entry points:

* `scripts/review_real_output_text.py`
* `scripts/score_real_output_text.py`
* `scripts/random_quality_check_itineraries.py`
* `scripts/update_real_output_qa_index.py`

### Patch 126: Test-suite cleanup report

Extended `scripts/test_suite_audit.py` so it can write handover-ready report files:

* `docs/reports/test_suite_audit/latest.md`
* `docs/reports/test_suite_audit/latest.json`

Current result: `293/293` test modules are covered by named groups, with `0` full-only modules and `0` duplicate group entries.

No tests were deleted. The audit still shows one source-file contract candidate: `test_cleanup_final_regression.py`.

### Patch 127: Static data hygiene

Added `scripts/static_data_hygiene.py` plus handover reports:

* `docs/reports/static_data/hygiene_latest.md`
* `docs/reports/static_data/hygiene_latest.json`

Current result: destination registry validates with `693` destinations and `0` registry errors. Review signals are limited to:

* duplicate place alias across Finland/Sweden `Utö`
* service-like airport wording on `Tromsø Airport`
* transit-only summary marker

No static data was changed or deleted.

### Patch 128: Final cleanup report

Created this handover report so the next pass starts from current evidence instead of re-discovering state.

## What was deleted

No files were deleted in this pass.

The previous deletion patch already brought immediate deletion candidates to `0`. Current deletion audit still reports `0` immediate candidates and `187` held-back compatibility/dynamic-risk items.

## What was intentionally kept

* Top-level compatibility facades such as `itinerary_parser.py`, `generator.py`, `normalizer.py`, `pdf_exporter.py`, `image_matcher.py`, and `text_polish.py`.
* Parser/common compatibility facade imports still used by many tests/import paths.
* Static destination and alias records. The hygiene report is review-only.
* Real-output QA CLI script names. They are now thin wrappers but remain stable entry points.

## Unresolved risks / next targets

1. Normalizer/parser modules still import generation helpers in several places. This is the best next architecture cleanup target.
2. Day intro/title/render modules still call route-point helpers directly in some places. Future cleanup should move more of that truth into DayFacts/DayCopyPlan.
3. `test_cleanup_final_regression.py` still has source-file contract assertions. Review carefully before changing; do not reduce coverage.
4. Static data has a real cross-country alias collision for `Utö`. Keep until fixture-backed behavior decides how country disambiguation should work.
5. Real-output QA still has warnings but no errors on the standard seeded samples.

## Validation notes

Combined shell commands can time out in the sandbox even when their individual commands pass. In this pass:

* combined structural/real-output test command: TIMEOUT, then individual commands passed
* combined audit/index command: TIMEOUT after writing several reports, then QA index passed separately
* combined score/preview/random command: TIMEOUT after score checks, then preview and random checks passed separately

## Recommended next patches

1. Split normalizer dependencies that import `itinerary_generation.*` into neutral parser/shared modules.
2. Reduce route extraction inside day intro/title/render modules by consuming prepared DayFacts/transport facts.
3. Review the single source-contract test candidate and convert it to behavior-level assertions only if safe.
4. Use the static data hygiene report to add disambiguation tests before changing aliases.
5. Keep real-output QA CLI scripts thin; add new reusable logic inside `scripts/real_output_qa/` only.

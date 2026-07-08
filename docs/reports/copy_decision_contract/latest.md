# Copy Decision Contract Report

Patch: 139

## Purpose

Prevent symptom-only copy/title fixes by making day title, intro, and leisure selections explainable and testable.

## Owners

* `itinerary_generation/title_decision_contract.py` owns activity-title source priority and narrow-inclusion rejection.
* `itinerary_generation/title_brain.py` owns whole-day title decisions.
* `itinerary_generation/day_intro_writer.py` owns intro decision metadata for Day Brain intro copy.
* `itinerary_generation/day_leisure_writer.py` owns leisure/free-time decision metadata.
* Render/PDF layers consume selected text plus decision labels. They do not own source priority.

## Guarded failure classes

* Narrow included items, tickets, landmarks, or attractions overriding broader product titles.
* Activity days falling back to weak day titles.
* Day intros falling through to admin/report-style fallback ownership.
* Real-output review reports hiding why a title or intro was selected.

## Regression coverage

* `tests/test_copy_decision_contracts.py`
* `tests/test_real_output_quality_gate_norway_regression.py`
* real-output scoring and markdown review reports

## Current status

* Parser/generation ownership audit signals: 13
* Module ownership audit: overworked files 0, long functions 0
* Test-group hygiene: 295/295 grouped

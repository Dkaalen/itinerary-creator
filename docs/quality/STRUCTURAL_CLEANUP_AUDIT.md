# Structural cleanup and ownership audit

This note documents the cleanup guardrails added after the real-output QA phase.
The goal is to keep the app healthy while avoiding risky mass rewrites.

## Ownership changes

### Text cleanup rules

Canonical rule tables now live in:

* `shared/text_cleanup_rules.py`

Parser cleanup, client polish, and real-output QA should import from that shared
module instead of maintaining separate typo/replacement tables.

Compatibility facades remain in:

* `parser_modules/text_cleanup.py`
* `text_polish_modules/text_cleanup_rules.py`
* `text_polish_modules/text_cleanup.py`

### Real-output QA

The previous single large `scripts/real_output_text_quality.py` module is now a
compatibility facade over:

* `scripts/real_output_qa/models.py`
* `scripts/real_output_qa/rules.py`
* `scripts/real_output_qa/segments.py`
* `scripts/real_output_qa/rendering.py`
* `scripts/real_output_qa/scoring.py`
* `scripts/real_output_qa/serialization.py`

CLI behavior should stay the same.

### Transport facts

Fact-only transport extraction now has a canonical model:

* `itinerary_generation/transport_domain/facts.py`

Use `build_transport_facts(row)` when a caller needs transport truth. Do not
re-parse route/place truth in rendering or QA unless the canonical model cannot
answer the question yet.

## Audit tools

Run these after structural patches:

```powershell
python scripts/module_ownership_audit.py
python scripts/test_group_hygiene.py
python scripts/export_destination_registry.py --validate-only
```

Reports are written under:

* `docs/reports/module_ownership_audit/`
* `docs/reports/test_group_hygiene/`
* `docs/reports/static_data/`

## Safe deletion policy

Facade-like modules are now easier to identify, but they should not be deleted
from an audit report alone. Delete only when all of these are true:

1. no production imports remain
2. no public compatibility contract remains
3. targeted tests pass
4. `python scripts/import_smoke.py` passes
5. `python scripts/architecture_guards.py` passes

## Next cleanup targets

The latest audit still shows large modules and long functions. The next safe
step is not broad deletion; it is focused function splitting in the files with
real behavior ownership:

* `itinerary_generation/day_facts.py`
* `parser_modules/place_parsing.py`
* `parser_modules/effective_type_detection.py`
* `itinerary_generation/description_templates.py`
* `itinerary_generation/activity_titles_core.py`

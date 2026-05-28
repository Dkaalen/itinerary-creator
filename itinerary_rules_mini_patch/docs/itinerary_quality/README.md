# Itinerary Output Rules Mini Patch

This folder captures the reusable output rules agreed during the itinerary-generator QA sessions.

It is intended to be committed into the repository and used as the source of truth for future patches, regression tests, and manual QA. These rules are deliberately general; they are not tailored to one specific itinerary.

Recommended usage:

1. Read `itinerary_output_rules.md` before changing parser, generator, inclusions, transport, PDF, or preview logic.
2. Use `forbidden_output_rules.md` as the basis for automated regression tests.
3. Use `quality_gate_checklist.md` before sending or deploying a patch.
4. Use `transport_wording_rules.md` as the canonical wording guide for all transport rows.
5. Add real customer-style inputs under `tests/fixtures/real_inputs/` and update `real_input_fixture_expectations.md` with expected outcomes.


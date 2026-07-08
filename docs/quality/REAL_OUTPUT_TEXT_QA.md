# Real output text QA

Patches 63-64 add a readable review runner and deterministic scoring layer for real Excel itinerary outputs.

## Patch 63: readable review runner

Use this when the goal is to inspect the generated product text, not just see pass/fail.

```powershell
python scripts/review_real_output_text.py --sample-size 5 --seed 6200
```

By default it writes both files below:

* `docs/reports/real_output_text_reviews/real_output_text_seed_<seed>.md`
* `docs/reports/real_output_text_reviews/real_output_text_seed_<seed>.json`

The markdown report shows:

* fixture id, workbook, sheet, tags, seed
* trip title, subtitle, route, journey overview
* score issues with location and excerpt
* a human-output focus section for title, intro and leisure copy
* each day title, city, intro
* source-row excerpts
* transport, accommodation, activity, leisure, and optional-experience text
* included, optional, and not-included sections

Exact rerun examples:

```powershell
python scripts/review_real_output_text.py --fixture "Standard-Itinerary-Finland.xlsx::106" --seed 7007
python scripts/review_real_output_text.py --workbook Finland --sample-size 4 --seed 7007
python scripts/review_real_output_text.py --sample-size 6 --seed 7007 --stdout
```

## Patch 64: scoring report

Use this when the goal is a compact machine-readable quality signal.

```powershell
python scripts/score_real_output_text.py --sample-size 5 --seed 6200
```

The JSON report includes per-candidate score, error count, warning count, issue codes, locations, and excerpts.

The scoring layer currently checks for:

* render failures and missing rendered days
* missing trip title or subtitle
* banned weak generated phrases
* supplier typo leaks
* unsafe `3/4-star` source becoming definite `4-star hotel`
* currency codes used as route/day cities
* multi-activity days saying the rest of the day is open
* activity days using full-leisure wording
* full leisure days using remaining-time wording
* return visits using first-arrival welcome wording
* city/activity mismatch sentences, especially overnight-train timing bugs
* transfer phrases treated as place names
* transport-like products rendered as activities
* typoed activity row types such as `Actvity Upgrade`
* repeated day intros
* raw optional-experience supplier blobs
* weak journey-overview labels such as `Journey Arc`
* weak arrival intros that describe output structure instead of the trip
* repetitive or admin-style free-time copy
* suspicious AM/PM time ranges such as `12:00 AM - 4:00 PM`
* narrow extracted ticket titles overriding broader supplier products

## Severity rules

Errors should fail random QA. Warnings should be reviewed but do not fail the default random checker yet.

Examples of errors:

* crashes
* no rendered days
* banned generated phrases
* factual hotel-star upgrades
* known high-risk supplier typos such as `Free wifi`, `Date dependant`, `Actvity`
* multi-activity false open-time claims
* currency codes used as cities

Examples of warnings:

* raw optional-experience blobs
* typo cleanup gaps in accommodation text, such as `Centraly`
* transfer phrases used as place names
* transport products rendered as activities
* activity city mismatch sentences
* repeated/generic phrasing

## Recommended workflow

1. Run `review_real_output_text.py` on a small seeded random sample.
2. Read the markdown report.
3. Run `score_real_output_text.py` to capture issue codes.
4. Fix root causes, not just the exact sentence.
5. Promote the fixture id and issue into a named regression test.
6. Run a new seed.

## Related QA tools

Regression promotion:

```bash
python scripts/promote_real_output_regression.py --seed 7007 --fixture "Standard-Itinerary-Iceland.xlsx::8D RW" --name activity-upgrade-typo-classification --issue-code typoed_activity_type_seen --expected-behavior "Activity Upgrade rows must not become destinations."
```

Preview/PDF-facing render text guard:

```bash
python scripts/preview_pdf_text_guard.py --sample-size 4 --seed 6200
```

Fixture tag index:

```bash
python scripts/tag_real_excel_fixture_bank.py
```

QA index:

```bash
python scripts/update_real_output_qa_index.py --sample-size 5 --seed 6200
```

## Patch 125 maintenance note

The CLI scripts stay thin. Reusable review, scoring, markdown, random-check, and QA-index logic lives under `scripts/real_output_qa/`:

* `selection.py` selects fixture candidates and builds rendered reviews.
* `markdown.py` owns readable review report formatting.
* `score_reports.py` owns compact JSON score report assembly.
* `random_checks.py` owns seeded random quality-check report assembly.
* `indexing.py` owns QA-index markdown/json generation.

The old script names remain as compatibility entry points for validation commands and tests.

## Patch 131-138 quality gate note

The Norway winter output regression is stored at:

* `tests/fixtures/real_inputs/norway_winter_output_quality_regression.txt`

It protects the PDF-facing issues found in the Norway sample: journey overview wording, Day 1 arrival intro, free-time copy, broad activity titles, supplier typo cleanup, and suspicious time-range warnings.

## Patch 139 decision-contract note

Title, intro, and leisure/free-time copy now expose decision metadata instead of relying on silent fallback chains.

The markdown review report includes title and intro decision sources for each day. The scoring layer can now fail output where:

* an activity-day title comes from a weak fallback or narrow included item
* an intro falls through to admin-style fallback ownership
* a broader product title is overridden by a ticket, landmark, or inclusion fragment

Decision-contract tests live in:

* `tests/test_copy_decision_contracts.py`

The main ownership rule is: renderer/PDF code consumes selected copy and decision labels; it must not rediscover title, intro, or leisure source priority.

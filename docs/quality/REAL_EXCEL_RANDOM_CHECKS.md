# Real Excel random quality checks

Patch 62 adds the uploaded standard itinerary and calculator workbooks as a real fixture bank for Day Brain/product-output testing.

## Fixture bank

The workbook manifest lives at:

`tests/fixtures/real_excel_inputs/manifest.json`

It indexes 10 workbooks and the extractor currently finds 97 candidate itinerary sheets across them.

## Why this exists

Small hand-written fixtures catch known regressions. The real Excel bank is for catching root causes across varied supplier/calculator inputs. When Day Brain, Sub-Brain, parser, title, trip, hotel, or copy logic changes, run a few random candidates rather than only checking the case you just fixed.

## Recommended workflow

Run a seeded sample while developing:

```powershell
python scripts/random_quality_check_itineraries.py --sample-size 5 --seed 6200
```

Then run a new random sample after fixing anything:

```powershell
python scripts/random_quality_check_itineraries.py --sample-size 5 --seed random
```

Save selected extracted text if you want to inspect the exact rows:

```powershell
python scripts/random_quality_check_itineraries.py --sample-size 5 --seed random --write-selected-text tmp\selected_excel_fixtures
```

Use `--all` only for a deeper manual sweep. It can be slow because it renders many real itineraries.

## Current hard checks

The random checker fails on:

* parser/render crashes
* no parsed rows
* no rendered days
* banned generated phrases
* unsafe `3/4-star` → definite `4-star hotel` disappearance
* supplier typo leaks such as `Date dependant`, `Funicual`, `Profesional`, `Free wifi`, `aiport`, `doulbe`, `milage`
* `Western Norway` title while Tromsø is present
* multi-activity days saying the rest of the day is open

## Validation proof

`python scripts/run_validation_proof.py` now includes a deterministic real Excel sample:

```powershell
python scripts/random_quality_check_itineraries.py --sample-size 4 --seed 6200
```

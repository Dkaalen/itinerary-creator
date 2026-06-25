# Golden Input Quality Sprint

Purpose: move the app from architecture cleanup into real end-to-end itinerary quality hardening.

## Source corpus now available

The repo now contains a pre-extracted JSONL fixture from the two real Vipin Nordic calculator workbooks supplied during the quality sprint kickoff.

- Fixture: `tests/fixtures/real_inputs/vipin_nordic_calculator_corpus_items.jsonl`
- Manifest: `tests/fixtures/real_inputs/vipin_nordic_calculator_corpus_manifest.json`
- Latest report: `docs/reports/vipin_nordic_calculator_corpus_report.md`
- Bad-output log: `docs/reports/vipin_nordic_calculator_bad_outputs.jsonl`

The binary Excel workbooks are intentionally not committed. The extracted JSONL keeps the real supplier rows stable and traceable while avoiding large spreadsheet files in the app repo.

## Inventory

- Real Vipin calculator rows: 5,557
- Source workbooks: 2
- Sheets with extracted rows: 307
- Top source types:
  - transfer: 2,001
  - activity: 1,891
  - hotel: 1,141
  - day overview: 211
  - leisure: 86
  - arrival: 32

## Latest full-corpus smoke result

Command shape:

```powershell
python .\scripts\vipin_excel_corpus.py `
  --items-jsonl tests\fixtures\real_inputs\vipin_nordic_calculator_corpus_items.jsonl `
  --report docs\reports\vipin_nordic_calculator_corpus_report.md `
  --bad-jsonl docs\reports\vipin_nordic_calculator_bad_outputs.jsonl `
  --report-label VIPIN_FULL `
  --workers 4 `
  --chunk-size 5
```

Latest result:

- Corpus rows checked: 5,557
- Parsed output rows: 5,438
- Parser exceptions: 0
- Whole-corpus generation smoke: passed
- Average parser confidence: 97.5%
- Rows under 80 confidence: 192

## Current quality backlog from the real corpus

The latest run has cleared the overlong-title and supplier-prose-title categories. The next product-quality targets are:

1. Missing parsed city for a small set of sparse activity/transfer rows.
2. Hotel-name extraction misses for malformed accommodation rows.
3. Cost/calculator rows and malformed header-like rows still appearing in the extracted corpus and needing better classification/reporting.
4. Unexpected skips from sparse rows that look itinerary-like but have too little usable supplier text.
5. Broader preview/PDF parity checks using the same golden inputs.


## Batch 18 title/prose boundary cleanup result

Batch 18 kept the one-responsibility-per-file rule by moving title/prose boundary heuristics into `parser_modules/title_prose_boundaries.py`, leaving `parser_modules/title_cleanup.py` as the orchestrator.

Improvement from the Batch 17 checkpoint:

- Overlong titles: 86 → 0
- Activity/supplier prose used as title: 63 → 0
- Rows under 80 parser confidence: 196 → 192
- Missing route origin flags: 101 → 97
- Missing route destination flags: 87 → 82

Key fixes locked with regression tests:

- Earliest title/prose boundary is chosen, so early text like `Prepare to explore...` beats later prose markers.
- Repeated-subject descriptions become compact titles, e.g. `Seljalandsfoss Waterfall Seljalandsfoss...` → `Seljalandsfoss Waterfall`.
- Long train/coach metadata becomes compact transport titles.
- Rental-car day-overview rows become `Pick-up rental car`.
- Hotel and cable-car rows no longer leak long inclusions or descriptive body text into the title.

## Batch 17 title/prose cleanup result

Batch 17 used the real Vipin corpus to harden title cleanup and row typing. The full run stayed stable with zero parser exceptions and generation smoke still passed.

Improvement from the previous full-corpus checkpoint:

- Overlong titles: 173 → 86
- Activity/supplier prose used as title: 82 → 63
- Rows under 80 parser confidence: 205 → 196
- Missing hotel name flags: 102 → 93
- Missing parsed city: 9 → 8

Key fixes locked with regression tests:

- Day overview rows remain Day Overview even when their prose mentions flights/trains/buses.
- Long activity prose can extract compact product titles such as `Ultimate Icelandic Adventure Tour`.
- Long-distance bus/coach transfers become compact transport titles.
- Private point-to-point transfers strip address/procurement notes from the title.
- Leading known-place titles can infer missing city, e.g. `Helsinki Hop on Hop off 24 Hr ticket`.

## How this should be used

Use this corpus as the first regression gate for future product-quality patches. The intended flow is:

1. Patch parser/generation/renderer behavior.
2. Run the representative fixture test:

```powershell
python -m pytest tests\test_vipin_full_corpus_fixture.py -q
```

3. Run the full Vipin corpus report when the patch touches parser, titles, grouping, source fidelity, or transport wording.
4. Compare `docs/reports/vipin_nordic_calculator_corpus_report.md` before and after the patch.
5. Lock important fixes with focused unit/regression tests.

This is not a normal-user feature. It is a developer quality harness for turning real supplier input into client-ready itinerary output.

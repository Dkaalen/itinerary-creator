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
- Parsed output rows: 5,439
- Generated editable titles checked: 4,194
- Parser exceptions: 0
- Rows skipped by parser: 118
- Whole-corpus generation smoke: passed
- Average parser confidence: 99.4%
- Rows under 80 confidence: 0

## Current quality status from the real corpus

The latest run has cleared the deterministic parsed-output defect buckets that were targeted in the post-cleanup sprint:

- Missing parsed city: 8 → 0
- Missing hotel name: 93 → 0
- Missing route origin: 97 → 0
- Missing route destination: 82 → 0
- Missing room category: 80 → 0
- Weak title: 6 → 0
- Missing hotel nights: 2 → 0
- Unexpected skip: 35 → 0
- Rows under 80 parser confidence: 192 → 0

The remaining bad-output log categories are source-data/reporting categories, not deterministic parser-generated client-output defects:

- missing_source_city: 381
- missing_source_date: 87
- missing_source_day: 85
- non_itinerary_type: 65
- missing_source_type: 21

The only remaining parser review flag is `very_long_supplier_text: 324`, which is retained as a developer review signal rather than normal-user UI.

## Batch 19 real-corpus output quality, parity, and editor polish result

Batch 19 moved the post-cleanup sprint to complete by hardening the app against real extracted Vipin calculator rows and representative golden-input preview/PDF output.

Key fixes locked with regression tests:

- Sparse city inference now uses nearby real itinerary context without allowing numeric night/count cells such as `2.0` to become cities.
- Hotel parsing now handles Excel serial dates, malformed star-hotel rows, room quantities, suites, igloos, chalets, studios, and meal-text leakage.
- Route extraction now handles Norway in a Nutshell, timed multileg routes, airport flights, trains, buses, coaches, and local/self-transfer summaries without noisy route flags.
- Calculator/header/report-only rows are reported as source-data cases instead of parser output failures.
- Preview/PDF parity smoke now covers multiple representative real fixture itineraries.
- Editor design-polish guards now read the split frontend source files and keep advanced/debug-only controls out of the normal render path.

Validation checkpoint:

```text
Full Vipin corpus: 5,557 rows, 0 parser exceptions, 99.4% average confidence, 0 rows under 80 confidence, generation smoke passed
Focused parser corpus tests: passed
Preview/PDF parity and editor no-bloat tests: passed
Baseline compile/node/import smoke: passed
```


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

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
- Average parser confidence: 97.3%
- Rows under 80 confidence: 205

## Current quality backlog from the real corpus

The latest run exposes the next product-quality targets:

1. Overlong generated/parsed titles, especially transfer and day-overview prose.
2. Day overview rows being treated as titles instead of structured day text.
3. Activity supplier prose leaking into title fields.
4. Missing parsed city for a small set of activity/transfer rows.
5. Cost/calculator rows and malformed header-like rows still appearing in the extracted corpus and needing better classification/reporting.

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

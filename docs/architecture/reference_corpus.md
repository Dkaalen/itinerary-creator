# Itinerary Reference Corpus — IH1

## Purpose

The reference corpus records supplied examples without making them a production
source of truth. It is used for characterization, validation, and the planned
Iceland group-tour domain work.

Runtime parsing and rendering do not import this corpus in Patch IH1.

## Version

`ih1-v1`

The version contains:

- 643 standard service templates across 100 destinations
- 163 clean activity references across 15 catalogue cities
- 15 Iceland itinerary sheets:
  - 5 self-drive sheets (`SD`)
  - 5 summer group-tour sheets (`GTS`)
  - 5 winter group-tour sheets (`GTW`)
- 402 retained Iceland rows, including base itinerary, optional upgrades, transfer packages, supplements, and extra-night rows

## Files

```text
itinerary_generation/data/reference_corpus/ih1-v1/
├── standard_input_templates.tsv
├── clean_activity_inputs.tsv
├── iceland_standard_itinerary.json
└── manifest.json
```

`manifest.json` stores schema/version metadata and SHA-256 checksums for every
corpus file and original supplied source.

## Data ownership

The corpus preserves both source and canonical fields:

- Source destination/city text remains unchanged.
- Canonical place names are stored separately.
- Iceland spreadsheet rows retain the original sheet, Excel row number, day,
  row type, source text, URL, comments, and commercial fields where populated.
- Conditional phrases remain in the source text and are indexed separately for
  regression testing.

## Validation policy

Errors represent schema or provenance failures and block the corpus gate.
Warnings represent source-data findings that future patches must handle safely.

The initial warning baseline intentionally includes examples such as:

- Catalogue city differing from the activity location
- Duplicate clean activity rows
- Missing or malformed time labels
- Ambiguous multiple time options
- Suspiciously long time ranges
- A summer package title without an explicit summer marker

Warnings must not be silently "fixed" during loading. Later domain code should
preserve the source facts, attach diagnostics, and avoid inventing corrections.

## Regeneration

The corpus can be rebuilt with:

```powershell
python .\scripts\build_reference_corpus.py `
  --standard-inputs <standard-inputs.txt> `
  --activities <clean-activities.txt> `
  --iceland-workbook <Standard-Itinerary-Iceland.xlsx>
```

The builder only reads `SD`, `GTS`, and `GTW` sheets. Resort sheets, calculation
sheets, and unrelated workbook tabs are excluded.

## Future consumers

Planned patches will use the corpus to characterize and test:

1. A dedicated group-tour package/day contract
2. Iceland group-tour parsing and package-day mapping
3. Preview, editor, inclusion, and PDF parity
4. Later self-drive domain support

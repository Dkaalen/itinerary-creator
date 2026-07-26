# Patch 15 — Workbook Authority, Provenance, Identity, and Cache Contract

## Production authority

The sole production Local Library authority is
`calculator.library_authority`. It exposes one immutable read contract with:

- authority identifier;
- resolved workbook path;
- SHA-256 content fingerprint;
- supported worksheets;
- normalized immutable records;
- immutable currency rates;
- workbook diagnostics;
- cache status and invalidation reason.

The authority reads
`data/Calculation-template-Inputs-fixed-outline-restored.xlsx`. Production
Local Library code must not substitute CSV, JSON, Supabase, SQLite, Google
Sheets, or an external API for this workbook.

## Stable identity

An authoritative record is identified by the tuple:

`authority + source workbook + source worksheet + source row`

Display text, supplier name, price, and URL are not identity inputs. Therefore:

- editing display text does not change source identity;
- identical-looking rows in different worksheets cannot collide;
- identical-looking rows on different worksheet rows remain distinct;
- intentional duplicate workbook products are not merged.

Synthetic test/import rows without workbook provenance retain a deterministic
fallback identifier, but that fallback is not used for authoritative workbook
records.

## Provenance lifecycle

The browser payload transports workbook, worksheet, row, and library identity
as hidden metadata. Selection copies that metadata into the Calculator row.
The metadata survives:

1. browser state and recovery;
2. Python Calculator state;
3. saved-project serialization and reconstruction;
4. Calculator-to-generator parsing and normalization;
5. render source-row identity;
6. Excel export as an internal custom document property.

Supplier URLs remain internal metadata. They are not inserted into client-facing
Calculator input or generated copy.

## Cache lifecycle

The cache key includes the resolved workbook path and a versioned SHA-256
fingerprint of workbook bytes. This catches same-size and restored-mtime edits.

- unchanged content returns an immutable cached snapshot;
- changed content reports `workbook_content_changed` and reparses;
- explicit clearing reports `explicit_cache_clear`;
- a failed parse never replaces a known-good authority snapshot;
- explicit clearing also removes the prepared browser payload and browser
  acknowledgement, forcing rehydration;
- browser component schema and ranking versions independently participate in
  the browser payload fingerprint.

Consumers receive tuples, frozen records, and read-only currency-rate mappings,
so they cannot mutate globally cached authority state.

## Excel export

The canonical export mutation plan carries source provenance separately from
cell pricing decisions. Renderers write that lineage only as the internal
`BooknordicsLocalLibraryProvenance` custom workbook property. The property does
not change visible template cells, formulas, formatting, or Calculator state.

# Local Library ranking specification

## Authority

`calculator/library_ranking.py` owns the versioned, JSON-compatible Local Library ranking specification.

The same specification is:

1. consumed by `calculator/library_search.py` for the Python reference search;
2. added to the Calculator payload by `app_modules/calculator_component_payload.py`;
3. consumed by the namespaced `calculator_grid_library_normalization.js`, `calculator_grid_library_index.js`, and `calculator_grid_library_search.js` modules for production browser autocomplete.

JavaScript owns browser execution and indexing, but it does not maintain separate field weights, match weights, worksheet routes, aliases, or tie-break rules.

## Normalization

Search normalization is intentionally stable and parity-tested:

- lowercase text;
- transliterate `ø` to `o`, `æ` to `ae`, and `å` to `a`;
- apply Unicode NFKD decomposition;
- remove combining marks;
- replace punctuation and other non-ASCII alphanumeric characters with spaces;
- collapse repeated whitespace.

This makes `Flåm` and `Flam` equivalent and prevents punctuation from changing ranking.

## Match classes

Each configured field uses the same ordered match classes:

1. whole normalized query equals the whole field;
2. whole normalized query starts the field;
3. whole normalized query occurs in the field;
4. exact query-token match;
5. query-token prefix match;
6. weaker query-token substring match.

The versioned specification contains the numeric weights. Strong travel-element and contextual matches therefore beat weak supplier, comment, or substring matches without duplicating constants in JavaScript.

## Context and worksheet routing

The specification owns the ordered worksheet routes for Hotels, Transfers, Transport, Activities, and General rows. Context bonuses use:

- expected worksheet;
- calculator row type;
- country present in the edited row text;
- exact or textual supplier context.

## Norway in a Nutshell compatibility

`Norway in a Nutshell` is a query-gated cross-type alias.

When the query contains that exact normalized phrase:

- Calculator row type `Activity` or `Transfer` is compatible;
- source worksheets `Activities`, `Transfers`, and `Transport` are compatible;
- source row types `Activity`, `Transfer`, and `Transport` are compatible.

This preserves the workbook’s real source identity while allowing Oslo, Bergen, and Flåm/Flam products stored under Transport-related rows to appear for either Activity or Transfer searches.

## Deterministic ordering

Equal scores are ordered by:

1. source worksheet;
2. Excel source row;
3. generated display label;
4. library ID.

Intentional duplicate rows remain separate. Worksheet, source row, and library ID are never merged or rewritten.

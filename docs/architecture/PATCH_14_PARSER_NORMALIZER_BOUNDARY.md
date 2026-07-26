# Patch 14 — Parser and Normalizer Boundary

## Supported flow

The production input path is explicit:

`raw text → parse_itinerary() → parsed source rows → normalize_itinerary_rows() → domain-enriched normalized rows → render artifact`

The raw parser extracts source-shaped facts only. It owns row splitting, day/type/date detection, source text and URL metadata, explicit city extraction, hotel source fields, optional/commercial source state, and stable parsed-row identity.

The parser does not assign semantic product types, route endpoints, canonical route facts, or contextual cities. Contextual city propagation, semantic classification, route-aware review metadata, source-aware product classification, and client-facing source-row standardization begin at normalization.

## Public APIs

The supported parser API is the explicit `itinerary_parser.__all__` surface. It contains `parse_itinerary` and the established extraction helpers used by application callers.

The supported normalizer API is the lazy `normalizer.__all__` surface:

- `normalize_row`
- `normalize_itinerary_rows`
- `warn_suspicious_city`

Production consumers outside `parser_modules` do not import parser internals. Reusable lexical contracts now have neutral owners:

- `shared.row_type_values`
- `shared.source_text_cleanup`
- `shared.source_time`
- `itinerary_domain.input_row_quality`
- `itinerary_domain.source_place_values`
- `itinerary_domain.source_route_parsing`

## Field and mutation policy

- Parsed rows retain source fields and unknown mapping fields.
- Normalization deep-copies every input row and does not mutate caller-owned mappings or nested values.
- Unknown fields are retained unchanged unless a named downstream domain owner deliberately enriches that field.
- Missing dates remain blank rather than being invented.
- Source URLs remain metadata.
- `row_id`, worksheet, source-row, Local Library identity, and other provenance fields survive normalization.
- Identical-looking source rows are not merged. Source identity, not display text, distinguishes them.

## Semantic ownership

`itinerary_domain.row_type_detection` owns generic semantic row-type detection.

`normalizer_modules.domain_enrichment` owns the ordered enrichment boundary:

1. Preserve explicit source-owned group-tour and commercial package types.
2. Detect a semantic candidate from generic source type and text.
3. Extract source route hints without declaring canonical route truth.
4. Apply source-row text standardization.
5. Project canonical route facts only for review-quality evaluation.
6. Apply source-owned Activity exceptions.

`normalizer_modules.source_row_standardization` owns the client-facing source-row decisions formerly performed during parsing.

Canonical transport facts remain owned by `itinerary_generation.transport_domain`. Raw parsing does not import that package or write route endpoints.

## Context and quality ownership

`normalizer_modules.context.fill_missing_context_cities` is the contextual-city authority. The parser no longer carries previous-city state or parses route-shaped text to decide whether a blank city may be filled.

`itinerary_domain.input_row_quality` owns deterministic input review flags and confidence scoring for both parsed and normalized rows. Raw rows skip route-completeness checks; normalized rows opt into them after route facts are available.

## QA consumer migration

The Vipin workbook corpus runner now evaluates the supported parser → normalizer pipeline rather than treating parser output as final client output. This exposed and fixed one hidden normalizer defect: a compact parser title from one-line `Day N:` activity prose is preserved instead of being expanded back into a long sentence. Multi-line group-tour day headings retain their specialized domain title behavior.

## Idempotence and parity

Normalization is idempotent. Re-normalizing an already normalized row preserves:

- Input review metadata
- Transport titles and route hints
- Hotel room and bed descriptions
- Activity product source titles
- Group-tour commercial row types
- Norway in a Nutshell contracts
- Unknown fields and source provenance

The real-input corpus verifies 484 rows across 19 fixtures with exact first-pass parity against the Patch 13 baseline and exact second-pass equality.

## Retired parser-owned modules

The following responsibilities were removed from `parser_modules` rather than retained as forwarding facades:

- `contextual_city.py`
- `effective_type_detection.py`
- `effective_type_priority.py`
- `effective_type_rules.py`
- `place_parsing.py`
- `place_values.py`
- `route_parsing.py`
- `row_quality.py`
- `row_text_standardization.py`
- `text_cleanup.py`
- `time_duration.py`
- `time_finders.py`
- `time_normalize.py`
- `time_parsing.py`
- `time_tokens.py`
- `transport_titles.py`

Their active responsibilities now have direct shared, domain, or normalizer owners.

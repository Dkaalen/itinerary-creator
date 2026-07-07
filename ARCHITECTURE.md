# Itinerary App Architecture

## Product rule

Every module should help create a client-ready itinerary faster, easier, more reliably, or more presentably.

## Current source-of-truth pipeline

Raw supplier rows flow through parser and normalizer modules, then into itinerary-generation modules that build canonical days, render documents, preview HTML, editor payloads, and PDFs.

## Day-copy ownership

- DayFacts owns factual day understanding only.
- Sub-brains own focused facts: accommodation, schedule, travel load, visit memory, supplier cleanup, titles, and trip-level framing.
- Intro Writer owns day intro prose.
- Leisure Writer owns leisure/free-time prose.
- Title Brain owns day titles.
- Trip Brain owns trip title and subtitle.
- Legacy facades may keep old imports stable, but they must not make competing copy/title decisions.

## Validation ownership

`scripts/test_groups.py` owns grouped test lanes. `scripts/run_test_group.py` owns execution, stage ranges, timeouts, and timing summaries.

Day Brain and Sub-Brain behavior must be covered by named groups, not only by the full fallback suite.

## Cleanup rule

Before deleting a compatibility module, confirm whether it is used by production imports, tests, dynamic app paths, or historical public imports. Prefer thin facades over duplicate logic when a legacy import path must remain.

# Refactor roadmap

This roadmap tracks the cleanup work for the itinerary app. The goal is to reduce bloat and hidden coupling without changing client-facing itinerary output unexpectedly.

## Already completed

- Added GitHub Actions test workflow.
- Fixed unsafe activity-title fallback in `itinerary_generation/canonical_builder.py`.
- Added safe `Experience` fallback when title cleaning removes unsafe supplier/admin text.
- Deduplicated activity inclusions and canonical included items.
- Added regression tests for title fallback and inclusion dedupe.
- Added renderer boundary guard tests so activity rendering keeps using canonical content.
- Replaced the `pdf_exporter.py` wildcard wrapper with explicit exports.
- Added a wrapper-export guard test.

## Main cleanup targets

### 1. Split `ui/day_blocks.py`

Current problem: `ui/day_blocks.py` mixes orchestration, HTML rendering, travel sequence logic, day overview parsing, rental overview parsing, and fallback block rendering.

Target structure:

- `ui/day_blocks.py` remains the thin row-order/grouping orchestrator.
- `ui/activity_blocks.py` renders activity and accommodation canonical blocks.
- `ui/travel_blocks.py` renders transfers, transport rows, self-arranged travel, and travel sequences.
- `ui/overview_blocks.py` renders day overview and rental overview blocks.
- `ui/leisure_blocks.py` renders leisure and cruise leisure blocks if useful.

Safety rule: move code first, keep behavior identical, then improve internals in later PRs.

### 2. Centralize title safety

Current problem: title safety decisions are spread across `title_safety.py`, `titles.py`, `content_engine.py`, `canonical_builder.py`, and some UI rendering paths.

Target direction:

- Keep unsafe-title detection in `itinerary_generation/title_safety.py`.
- Ensure canonical generation is the final safety boundary before rendering.
- Keep renderers from reading raw supplier/admin title fields directly.

### 3. Split `itinerary_generation/titles.py`

Current problem: one module handles activity titles, day titles, trip titles, route-specific titles, season/cover decisions, and special product naming rules.

Target structure:

- `activity_titles.py`
- `day_titles.py`
- `trip_titles.py`
- `route_titles.py`
- `cover_titles.py` or `season_titles.py`

Safety rule: keep public imports stable until all callers move over.

### 4. Reduce compatibility-wrapper ambiguity

Current problem: some wrappers are intentionally kept for stable imports, but wildcard exports can hide dependencies.

Target direction:

- Prefer explicit imports and explicit `__all__` in compatibility wrappers.
- Keep wrapper files only where they protect existing imports.
- Do not remove wrappers until app code and tests prove they are unused.

## PR discipline

Every cleanup PR should be small and focused:

1. One concern per PR.
2. No broad copy rewrites without tests.
3. Keep client-facing text stable unless a regression test requires a change.
4. Run `python -m pytest tests/`.
5. Run `python -m compileall -q .`.

## Current next step

Start with the safest `ui/day_blocks.py` split: move activity/accommodation rendering into a new focused renderer module while preserving the existing public `build_activity_block()` and `build_accommodation_block()` functions as wrappers during the transition.

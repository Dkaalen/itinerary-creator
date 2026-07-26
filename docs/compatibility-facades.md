# Compatibility facades

These modules are intentionally kept as stable public import paths while the
implementation is split into smaller packages. Do not delete them just because they look thin.

## Required top-level facades

| Facade | Current owner package | Why it stays |
| --- | --- | --- |
| `generator.py` | `itinerary_generation` | Older tests, scripts, and app code still import high-level generation helpers from `generator`. |
| `text_polish.py` | `text_polish_modules` | Shared text cleanup import path used broadly across parser, generation, PDF, UI, and tests. |
| `image_matcher.py` | `images` | Stable image-matching import path used by image UI and tests. |
| `pdf_exporter.py` | `pdf_exporter_modules.public_api` | Stable PDF export import path used by tests and legacy scripts. |

## Supported top-level APIs

These thin modules are not legacy compatibility facades. They are the official
application boundaries for their subsystems. Their explicit ``__all__``
surfaces define the supported imports, while implementation modules remain
private to their packages.

| Public API | Current owner package | Contract |
| --- | --- | --- |
| `itinerary_parser.py` | `parser_modules` | Supported raw-input parsing API. |
| `normalizer.py` | `normalizer_modules` | Supported itinerary-row normalization API. |

## Required package-level facades

Several `ui/*` modules intentionally wrap neutral render/generation helpers.
This keeps older HTML-facing imports stable while the canonical logic lives in
`itinerary_generation/*`.

Several `itinerary_generation/*` modules also remain as compatibility paths for
older imports while implementation details are split into focused modules.
Examples include `day_text.py`, `day_intro_planner.py`, and `source_identity.py`.

The chunky top-level export lists for `generator.py` and `pdf_exporter.py` now
live in package-owned `public_api.py` modules so the root files remain thin
compatibility surfaces only.

## Recently retired facades

Patch 57 removed verified-unreferenced debug/UI/render wrappers such as `app_modules/performance_telemetry_debug.py`, `app_modules/saved_project_storage_ui.py`, `pdf_exporter_modules/renderers.py`, `project_storage/status.py`, and `text_polish_modules/core.py`. Their replacement owners are direct package exports or focused implementation modules.

Patch 15/28 removed the verified-unreferenced HTML wrappers `ui/day_overview_blocks.py` and `ui/transport_row_blocks.py`. Their active owners are `ui/day_blocks.py` for day-overview HTML and `itinerary_generation/transport_render_blocks.py` for transport render blocks.

## Cleanup rule

A facade can only be removed when all of these are true:

1. Import search shows no app, script, or test imports remain.
2. The public symbols are available from a replacement module.
3. Regression tests pass without compatibility import assumptions.
4. The removal is done in a dedicated cleanup patch, not mixed into feature work.

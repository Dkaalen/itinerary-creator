# Refactor audit and split strategy

This audit records the current high-risk areas in the itinerary app and proposes safe, small pull requests for cleanup. The goal is to reduce bugs without changing the visual layout unexpectedly.

## Current rule of thumb

- Keep runtime changes small and focused.
- Prefer extraction with parity tests before behavior changes.
- Do not delete image or data assets until references are checked.
- Keep public wrapper modules stable until internal imports have moved.
- Avoid combining visual layout changes with parser/content changes.

## High-risk files

### `app_modules/itinerary_html.py`

This file currently coordinates trip metadata, cover content, summary pages, final pages, and a large inline CSS block. This makes small cover-page changes risky because they require editing a large mixed-responsibility file.

Recommended split:

1. Extract the CSS block into `ui/itinerary_styles.py`.
2. Extract cover page markup into `ui/cover_page.py`.
3. Extract summary/glance page markup into `ui/summary_pages.py`.
4. Keep `build_itinerary_html()` as a thin coordinator.
5. Add cover-page trip dates after the cover renderer is isolated.

Safe PR order:

- PR 1: Extract styles only, no HTML behavior change.
- PR 2: Extract cover page renderer, output should remain identical.
- PR 3: Add trip date range to cover page using the existing date resolver.

### `ui/day_blocks.py`

This file is still a mixed renderer/coordinator with activity, accommodation, transport, arrival, departure, leisure, overview, rental, and supplier-cleanup logic. Some canonical renderers already exist, but `day_blocks.py` still manually duplicates parts of that rendering.

Recommended split:

1. Make `build_activity_block()` delegate directly to `ui.canonical_blocks.render_activity_block()`.
2. Make `build_accommodation_block()` delegate directly to `ui.canonical_blocks.render_accommodation_block()`.
3. Move transport-related blocks to `ui/transport_blocks.py`.
4. Move arrival, departure, leisure, and cruise leisure blocks to `ui/simple_day_blocks.py`.
5. Move overview and rental blocks to `ui/day_overview_blocks.py`.
6. Remove unused imports after each extraction.

Safe PR order:

- PR 1: Delegate activity block only.
- PR 2: Delegate accommodation block only.
- PR 3: Move self-transfer/self-arranged transport blocks.
- PR 4: Move simple arrival/departure/leisure blocks.
- PR 5: Move overview/rental blocks.

### `itinerary_generation/canonical_builder.py`

This file is the right place for canonical client-facing decisions, but it still imports several helpers from `ui.render_helpers`. That creates a layer boundary problem: generation code depends on UI code.

Recommended split:

1. Move non-HTML display helpers into `itinerary_generation/display_facts.py`.
2. Keep HTML-specific helpers in `ui/render_helpers.py`.
3. Update `canonical_builder.py` to depend only on itinerary-generation modules and neutral utilities.

Safe PR order:

- PR 1: Copy one pure helper into `itinerary_generation/display_facts.py` and update one call site.
- PR 2: Continue moving helpers in small batches.
- PR 3: Remove now-unused UI helper imports.

### `itinerary_generation/transport.py`

This file holds route parsing, place cleanup, via-point handling, mode-specific labels, route-transfer detection, and primary transport title selection. It is rule-heavy and difficult to patch safely.

Recommended split:

1. Extract route parsing and route place cleanup to `itinerary_generation/transport_routes.py`.
2. Extract train labels to `itinerary_generation/transport_train.py`.
3. Extract flight labels to `itinerary_generation/transport_flight.py`.
4. Extract coach/bus labels to `itinerary_generation/transport_coach.py`.
5. Extract cruise/ferry labels to `itinerary_generation/transport_cruise.py`.
6. Keep `transport.py` as the stable public wrapper.

Safe PR order:

- PR 1: Extract route helpers with parity tests.
- PR 2: Extract train label function with parity tests.
- PR 3: Retry sleeper cabin wiring inside the train-specific module.
- PR 4: Extract coach title cleanup after train is stable.

### `app_modules/main_view.py`

This file owns most of the Streamlit workflow. It is manageable, but export handling should be isolated because PDF errors are currently hard to diagnose.

Recommended split:

1. Move export UI to `app_modules/export_workflow.py`.
2. Store last PDF export error in session state.
3. Show a clearer error summary when PDF creation fails.
4. Keep the existing HTML download path as a fallback.

Safe PR order:

- PR 1: Extract export UI without changing behavior.
- PR 2: Add clearer PDF error state and display.
- PR 3: Add tests around missing HTML path / failed PDF export wrapper behavior.

## Asset folders to audit before deleting anything

The repository has multiple image-related locations:

- `assets/cover_backgrounds`
- `image_bank/Default`
- `images`

These may all be valid. Do not delete them until code references are checked. The first safe step is to document intended ownership and naming rules for each folder.

Suggested asset audit steps:

1. List every image path referenced by code.
2. Compare with files present in image folders.
3. Mark unreferenced files as candidates, not deletions.
4. Delete only in a later PR after a manual visual check.

## Open red PR cleanup

Current red PRs should not be merged as-is. The useful ideas can be retried after the relevant modules are split:

- Train sleeper cabin label wiring should be retried after `transport_train.py` exists.
- Transport title noise cleanup should be retried after coach/bus labeling is isolated.
- Accommodation meal dedupe should be retried after canonical accommodation rendering is isolated and easier to test.

## Suggested next actions

1. Merge this audit document if CI passes.
2. Start with the smallest refactor: delegate `build_activity_block()` to `ui.canonical_blocks.render_activity_block()`.
3. Then delegate `build_accommodation_block()`.
4. Extract export workflow to improve PDF error diagnosis.
5. Return to the visible demo bugs after the relevant modules are smaller.

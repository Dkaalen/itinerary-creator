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

## Calculator frontend ownership

`calculator_grid_component/frontend/index.html` owns one deterministic script-loading order. `window.ItineraryCalculator` is the explicit registry and public boundary for split frontend domains; implementation ownership is divided by responsibility:

- `calculator_grid_caret.js`, `calculator_grid_keyboard.js`, `calculator_grid_cell_commits.js`, and `calculator_grid_formula_sync.js` own editing, navigation, commits, caret placement, and formula-bar synchronization.
- `calculator_grid_math.js`, `calculator_grid_currency.js`, `calculator_grid_formatting.js`, and `calculator_grid_formula_input.js` own formulas, financial calculations, currency conversion, and display formatting.
- `calculator_grid_toolbar_render.js`, `calculator_grid_grid_render.js`, `calculator_grid_status_render.js`, `calculator_grid_suggestion_render.js`, and `calculator_grid_render.js` own the separate rendering surfaces and shell composition.
- `calculator_grid_excel_actions.js`, `calculator_grid_sales_actions.js`, `calculator_grid_submission_actions.js`, `calculator_grid_shortcuts.js`, and `calculator_grid_actions.js` own commands and event binding without creating a second browser-state authority.

`calculator_grid_state.js`, `calculator_grid_state_controller.js`, and `calculator_grid_protocol.js` remain the grid-state and backend-protocol authorities. Browser recovery is owned by `calculator_grid_storage_core.js`, `calculator_grid_draft_repository.js`, and `calculator_grid_recovery_repository.js`, exposed through `ItineraryCalculator.storage`. Local Library retention, indexing, search, and projection are separate namespaced modules exposed through `ItineraryCalculator.library`.

## Application workflow ownership

Cross-workflow session decisions are split by responsibility rather than collected in one transition module:

- `workflow_navigation.py` owns application routes, workflow-stage normalization, and visible-stage resolution.
- `calculator_lifecycle.py` owns local Calculator import and Calculator-to-generator transitions.
- `project_session_transitions.py` owns transactional project open, switch, duplicate, delete, and save-failure state.
- `render_lifecycle.py` owns PDF and export-artifact invalidation.
- `image_projection_state.py` projects committed itinerary rows for image matching without mutating workflow state.
- `workflow_state.py` owns only defaults, clean reset, and plain snapshots.

`calculator_page.py` composes the page and component protocol. Backend validation policy lives in `calculator_action_policy.py`, while accepted navigation, import, download, generation, and backup actions are executed by `calculator_page_actions.py`. Repository operations remain below the application boundary and are not imported by these neutral transition owners.

## Streamlit design ownership

Application styling is composed centrally by `ui/styles.py`; page modules may expose keyed layout containers but must not inject competing CSS. Responsibility is split by surface:

- `ui/style_forms.py` owns shared controls and compact form sizing. Large work areas such as supplier input are re-expanded only by their surface owner.
- `ui/style_component_layout.py` owns cross-surface text fitting, shrink-safe Streamlit columns, responsive action rows, top bars, metrics and filter grids. It targets explicit `st.container(key=...)` namespaces rather than page-order selectors.
- `ui/style_input_workspace.py`, `style_calculator.py`, `style_project_browser.py` and `style_export.py` own their respective page surfaces.
- Custom editor and Calculator iframe styles remain inside their component packages and are not overridden by Streamlit page CSS.

Button wrapping, mobile stacking and long-value overflow are presentation contracts only; they must not move workflow, storage, Calculator or export decisions into the style layer.

## Saved-project storage ownership

The saved-project subsystem keeps transport, persistence, application state and UI responsibilities separate:

- `project_storage/http_client.py` owns the minimal PostgREST and Supabase Storage transport, including counted reads, explicit RPC calls and filtered patch operations.
- `project_storage/repository.py` owns itinerary metadata, version payloads, registered files, deterministic listing, owner/folder updates, Trash/restore and permanent cleanup. It has no Streamlit dependency.
- `project_storage/project_metadata.py` owns normalized owner, actor and logical folder/reference values. These labels organize work but do not authenticate users or grant access.
- `project_storage/project_results.py` owns immutable exact-count, bulk mutation and purge outcomes.
- `project_storage/version_writer.py` owns consistency-preserving project/version writes and compensating rollback.
- `app_modules/project_storage_service.py` is the application adapter. Streamlit UI modules must call this service rather than importing the repository directly.
- `supabase/migrations/` owns additive production schema changes. Streamlit startup must never attempt database DDL.

Project snapshots remain canonical in `itinerary_versions.payload`; Supabase Storage is reserved for actual files such as Calculator workbooks and PDF exports. Soft deletion retains versions and registered files until an explicit permanent purge. The Local Library workbook remains a separate repository-bundled authority.

## Visual editor frontend ownership

`visual_editor_component/frontend/index.html` is a thin shell. `editor_bootstrap.js` owns the complete script manifest and starts the editor only after every responsibility group has loaded. `window.ItineraryVisualEditor` is the single explicit public namespace and rejects duplicate module registration.

- `state.js` exposes read-only state snapshots.
- `serialization.js` owns payload collection and save-envelope construction.
- `editor_local_draft.js` owns browser-local recovery persistence.
- `editor_page_actions.js` owns generated and manual page operations.
- `render.js` owns rendering from the canonical prepared `RenderDocument` payload.
- `editing.js` owns editor lifecycle, manual save, and autosave scheduling.
- `streamlit_bridge.js` owns messaging to and from Python and initializes only when called by the bootstrap owner.

The retired `editor_assets.js` document-write loader, `commands.js` global re-export facade, and empty `editor_readiness.js` compatibility marker must not return. Editor modules may coordinate through their established internal runtime, but external consumers use only the registered namespace APIs.

## Day-intro writer ownership

`itinerary_generation/day_intro_writer.py` remains the stable public facade. Implementation is split into bounded owners:

- `day_intro_context.py` builds immutable fact/intent planning context.
- `day_intro_destination_context.py` owns destination identities, arrival wording inputs, and route-profile awareness.
- `day_intro_phrase_selection.py` owns intent-to-phrase selection.
- `day_intro_repetition.py` owns return-visit wording and first-arrival repetition protection.
- `day_intro_seasonal_context.py` derives season only from explicit source dates.
- `day_intro_rendering.py` owns decision metadata and final plain-text rendering.

Renderers consume the selected intro and decision labels; they do not recreate intro logic.

## Destination-content ownership

`itinerary_generation/destination_copy.py` and `destination_profiles.py` remain stable public facades. Their implementation is split into explicit owners:

- `data/nordic_destination_registry.py` builds canonical Nordic destination records.
- `destination_seasonal_variants.py` owns season-profile classification.
- `destination_content_lookup.py` owns direct-alias, polished-alias, and polished-unknown fallback order.
- `destination_arc_content.py` owns Journey Arc fallback copy.
- `destination_arrival_content.py` owns arrival-focus copy.
- `destination_leisure_content.py` owns leisure options, filtering, and prose.
- `destination_travel_day_content.py` owns destination-aware travel-day fallback prose.
- `destination_copy_variants.py` owns deterministic prose-variant selection only.
- `destination_content.py` and `destination_profile_copy.py` compose or re-export these owners.

Destination-specific overrides remain explicit. Unknown destinations follow a deterministic fallback path and continue to use the shared Nordic place-key authority.

## Experience-summary ownership

`itinerary_generation/summaries_experience.py` remains the stable public composition facade for compact Journey Arc experience phrases:

- `summaries_experience_signals.py` extracts source-backed activity, route, logistics, destination, and theme facts.
- `summaries_experience_candidates.py` owns ordered candidate generation and prioritization.
- `summaries_experience_deduplication.py` owns stable first-occurrence duplicate control.
- `summaries_experience_phrasing.py` owns logistics-only wording and compact phrase composition.
- `summaries_experience.py` composes the stages and preserves `describe_city_experience`.

The Journey Overview evidence layer continues to validate selected phrases against source rows.

## Route-point ownership

Stable APIs remain in `parser_modules.place_parsing`, `itinerary_generation.transport_domain.route_points`, and `itinerary_generation.transport_domain.routes`, while implementation ownership is split as follows:

- `parser_modules/place_values.py` owns parser city/place validation and normalization.
- `parser_modules/route_parsing.py` owns generic text-to-origin/destination parsing.
- `transport_domain/route_inference.py` owns row-aware source precedence and endpoint inference.
- `transport_domain/route_validation.py` owns canonical route-field and endpoint validation.
- `transport_domain/route_intermediate_stops.py` owns timetable, `via`, and multi-leg intermediate-stop extraction.
- `transport_domain/route_hubs.py` owns terminal suffixes, hub normalization, base-city reduction, and terminal detection.
- `transport_domain/route_points.py` owns cached public row-route access.
- `transport_domain/routes.py` composes endpoint, via, mode, confidence, and supplier-hint facts.

Intermediate stops never replace the final destination. Parser-owned route fields win only when they contain plausible place facts.

## Local Library workbook ownership

`calculator/library_workbook.py` remains the stable public loader and fingerprint-cache authority:

- `library_workbook_models.py` owns immutable result, diagnostic, formula-cell, and error contracts.
- `library_workbook_schema.py` owns required sheets, header discovery, schema validation, and currency rates.
- `library_workbook_formulas.py` owns XLSX formula XML, cached-value checks, and syntax validation.
- `library_workbook_rows.py` owns product-row detection and row-level validation.
- `library_workbook_diagnostics.py` owns stable diagnostic formatting.
- `library_workbook.py` owns workbook lifecycle, strict normalization orchestration, caching, and the existing public API.

The workbook remains the sole Local Library production authority. Duplicate source rows retain worksheet, Excel row, and library-ID identity.

## Validation ownership

`scripts/test_groups.py` owns grouped test lanes. `scripts/run_test_group.py` owns execution, stage ranges, hard timeouts, checkpoints, resume behavior, and timing summaries.

Every active pytest module belongs to at least one named group. Broad product lanes remain release-candidate authorities, while focused lanes cover Calculator browser behavior, formulas, validation, workbook import/export, realistic Calculator use, project management, rollback, cloud lifecycle, reconstruction, generation, and editor/picture integration.

Calculator browser workflows use explicit node-level stages. Other focused workflow stages contain at most two modules so they can be selected or resumed without losing coverage.

## Cleanup rule

Before deleting a compatibility module, confirm whether it is used by production imports, tests, dynamic app paths, or historical public imports. Prefer thin facades over duplicate logic when a legacy import path must remain.

## Cleanup proof tools

- `scripts/run_validation_proof.py` runs the compact Day Brain/Sub-Brain proof lane plus hosted-generation and output-regression scripts.
- `scripts/review_output_regression.py` protects the Norway sample that exposed star-rating, multi-activity-day, title, and supplier-cleanup regressions.
- `scripts/audit_legacy_facades.py` regenerates `docs/architecture/LEGACY_FACADE_AUDIT.md` after facade cleanup.
- `scripts/test_group_hygiene.py` proves that active test modules are grouped without stale or duplicate catalogue entries.

## Legacy deletion rule

Compatibility facades are kept only when they are real public import paths. Verified unreferenced debug, UI, or rendering wrappers should be deleted rather than preserved as noise.

## Quality ownership

`itinerary_generation/quality_row_selection.py` is the sole authority for normalizing quality rows and deciding which source rows are important to itinerary quality. Structural quality gates and operational health reporting consume that selector; they must not recreate `_as_rows`, `_is_important_row`, or `_important_rows` helpers.

Prepared client-output quality is evaluated once when `ItineraryRenderContext` is built, after final client sanitation. The immutable `ClientOutputQualityGateReport` stores both the deduplicated findings and its precomputed advisor assessment. Preview warnings, PDF readiness, real-output QA, and the health report reuse that same prepared report. PDF image findings are appended through `add_image_quality_issues` without rerunning document, source-fidelity, repetition, transport, or sanitation rules.

Responsibility boundaries remain distinct:

- `quality_row_selection.py` owns row selection.
- Structural and client-output check modules own rule evaluation.
- `advisor_quality.py` owns Ready / Minor edit / Major edit / Unusable calculation.
- Health and UI modules own report formatting only.

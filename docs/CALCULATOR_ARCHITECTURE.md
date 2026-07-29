# Calculator architecture

## Ownership

- `calculator/financial_rules.py` owns the versioned precision, commission scale, margin basis, formula-result kinds, and Excel precision-wrapper contract.
- `calculator/cell_formula_engine.py` is the authoritative financial engine and A1 dependency evaluator.
- `calculator/calculations.py` aggregates canonical row, total, and dashboard results.
- `calculator_grid_component/frontend/js/calculator_grid_math.js` is the immediate browser preview and is parity-tested against Python. Canonical row formulas remain NOK-based; the dashboard converts those totals through the saved EUR→NOK rate for EUR-first presentation.
- `calculator/formula_map.py` owns canonical Excel formulas.
- `calculator/workbook_export_plan.py` owns all calculator-to-workbook mappings, value kinds, formulas, currency rows, totals, payments, and blank-row decisions.
- `calculator/workbook_package_export.py` is the production package-renderer facade; it owns orchestration and the bounded export cache only.
- `calculator/workbook_package_cell_changes.py` validates and translates canonical plan cells into package changes.
- `calculator/workbook_worksheet_xml.py` owns worksheet row, cell, value, formula, and dimension XML mutation.
- `calculator/workbook_recalculation_xml.py` owns `calcPr` recalculation metadata.
- `calculator/workbook_zip_package.py` owns metadata-preserving XLSX ZIP cloning and approved part replacement.
- `calculator/workbook_export.py` retains an openpyxl renderer only as a mutable-workbook compatibility and parity-check API.
- `calculator/workbook_import.py` reads compatible calculation workbooks without rebuilding them.
- `calculator/state_serialization.py` owns JSON backup/schema migration.
- `calculator/date_links.py` owns the authoritative trip start, day-number offsets, and linked-versus-locked date relationships.
- `calculator/workbook_date_metadata.py` owns durable XLSX metadata for those date relationships; the visible workbook dates remain ordinary editable cells.
- `app_modules/saved_project_calculator_state.py` is the cloud-project persistence boundary.
- `calculator_grid_component/frontend/js/calculator_grid_keyboard.js` owns grid key handling and cell-to-cell navigation; `calculator_grid_cell_editing.js` owns edit commits and input behavior, not navigation.

## Frontend module boundary

`calculator_grid_component/frontend/index.html` is the single Calculator frontend initialization owner. It loads `calculator_grid_namespace.js` first and then registers domain modules in an explicit dependency order. The implementation intentionally remains framework-free and does not require a bundler.

`window.ItineraryCalculator` is the only public Calculator namespace introduced by the split. Its registry rejects duplicate module names, fails immediately when a required dependency is unavailable, freezes registered exports, and publishes only the supported browser APIs:

- `ItineraryCalculator.library` prepares the retained library bundle, performs browser-owned search, and applies selected workbook rows.
- `ItineraryCalculator.storage` persists the current draft, manages project-scoped recovery history, reports storage health, and restores selected snapshots.

The Local Library implementation is divided by responsibility:

- `calculator_grid_library_normalization.js`: versioned normalization and ranking-contract preparation.
- `calculator_grid_library_transport.js`: browser retention, fingerprint acknowledgement, and cache-miss recovery.
- `calculator_grid_library_index.js`: compact-row expansion and index construction.
- `calculator_grid_library_search.js`: worksheet routing, candidate scoring, and deterministic ordering.
- `calculator_grid_library_selection.js`: projection of one selected workbook row into one Calculator row.
- `calculator_grid_library_api.js`: the deliberately small supported public API.

Browser recovery is divided by responsibility:

- `calculator_grid_storage_core.js`: the shared IndexedDB contract, project-scoped records, storage health, byte accounting, migration, and recognized-namespace cleanup.
- `calculator_grid_draft_repository.js`: current-draft persistence and restoration eligibility.
- `calculator_grid_recovery_repository.js`: snapshot encoding, delta history, retention, pruning, and restoration orchestration.
- `calculator_grid_storage_api.js`: the deliberately small supported public API.

The retired multi-domain owners `calculator_grid_library.js` and `calculator_grid_draft_storage.js` are not compatibility surfaces. Production callers use the namespace APIs rather than depending on private functions or accidental script globals. Existing unsplit Calculator files retain their established behavior; Patch 8 does not convert the whole frontend to a new framework or module system.

## Browser workflow

The grid has two explicit modes:

- **Selection mode:** arrows move between cells; the first click on fetched or pre-filled data focuses the grid. Shift+Arrow extends one durable rectangular selection. Copy and paste operate on that selection: one copied value broadcasts across the selected range, compatible copied rectangles repeat across the destination, and external tab-separated blocks paste from the selected range’s top-left cell.
- **Edit mode:** click the active cell, double-click, press `F2`/`Enter`, or type; arrows move the caret and clipboard paste inserts plain text at the caret.

`Ctrl+D` repeats the top selected values down, `Ctrl+R` repeats the left selected values to the right, and `Ctrl+Shift+D` continues text-number sequences such as `Day 1`, `Day 2`. Dragging the fill handle uses the same numbered-series recognition while ordinary text remains a repeated fill. Every paste or fill records one history snapshot, so one Undo restores the complete operation. Bulk grid operations defer date propagation and financial recalculation until all destination cells have been updated, then perform one calculation and one render. Internal grid copies carry source coordinates for relative formula translation while plain TSV remains the cross-application clipboard contract.

The dashboard trip-start field is the authoritative itinerary date. Date cells explicitly carry either **linked** ownership with a day offset or **locked** ownership. Changing the trip start—or editing the linked Day 1 From date—shifts all linked From/To dates in one undoable operation while locked dates remain unchanged. Editing another date manually locks that cell; the Link dates and Lock dates actions let the user change ownership deliberately. Legacy backups and workbooks infer conservative relationships from Day labels and existing dates. Trip start, ownership modes, and offsets persist through cloud projects, JSON backups, project-scoped IndexedDB recovery, and internal XLSX metadata.

Browser edits are written to a project-scoped IndexedDB draft and synchronized to Streamlit after a short debounce. Opening a saved project selects its durable project namespace, while deleting the active cloud project or importing a local workbook detaches that namespace so the next unsaved workspace receives a fresh session key. Reopening an Excel workbook or Calculator backup is confirmation-gated whenever the latest browser/backend Calculator state differs from the saved snapshot or contains meaningful detached rows; clean workspaces still reopen directly. A capped local recovery history stores meaningful committed versions. The current draft has quota priority, inactive-project recovery histories are pruned before the active history, and only expired recognized Calculator namespaces are removed automatically. Local recovery failures remain non-blocking and are shown as a quiet status with details that distinguish browser recovery from Supabase project saving. The version panel can clear either recovery versions alone or all local recovery data for the active project; a full clear remains in effect until the next local edit. Save, export, generate, library navigation, and workspace navigation flush the latest state first.

A1 formulas support relative and absolute references, dependency recalculation, copy/fill translation, and circular-reference errors. Python and JavaScript are independently parity-tested.

### Bounded Chromium workflows

Calculator browser coverage is split by responsibility so every file runs independently below the 45-second command ceiling:

- editing and caret behavior
- navigation and focus
- clipboard and paste
- autocomplete and fetching
- formulas and currencies
- download and import
- component lifecycle and messaging
- drafts and recovery
- recovery storage resilience and quota handling

`tests/support/calculator_browser_harness.py` owns the shared production-asset loading, payload, Chromium launch, and recovery-quota fixtures. Browser test files must not duplicate that setup or depend on another browser test module.

## Financial parity

- Python owns the versioned financial rule contract and sends it to the component in every payload.
- Browser previews consume that contract for money, exchange-rate, percentage, commission, formula-result, and margin-shortcut behavior.
- Margin shortcuts target GP from actual `net_price_nok`, not supplier gross price, and clear only downstream sales-derived overrides.
- Money uses two decimal places; exchange rates and percentages use six. Rounding is decimal half-away-from-zero.
- Excel export wraps user formulas with canonical `ROUND` precision and import removes only those app-generated wrappers, preserving the original editable expression.
- `tests/fixtures/calculator_financial_parity_cases.json` covers browser, Python, saved-project, and Excel round-trip parity.
- `docs/CALCULATOR_FINANCIAL_RULES.md` documents the complete contract.

## Local Library autocomplete

- `calculator/library_ranking.py` owns the versioned normalization, field and match weights, worksheet routing, context bonuses, cross-type aliases, and deterministic tie-break specification.
- `calculator/library_search.py` is the Python reference implementation and consumes that canonical specification.
- `app_modules/calculator_component_payload.py` prepares and fingerprints the compact read-only Local Library payload and sends the exact ranking specification to the component.
- The namespaced Local Library modules under `calculator_grid_component/frontend/js/calculator_grid_library_*.js` are the production browser execution authority: normalization, retention, indexing, scoring, deterministic ordering, and selection projection have separate owners and share the canonical ranking payload.
- `calculator_grid_component/frontend/js/calculator_grid_suggestions.js` owns the in-grid suggestion lifecycle, debounce, focus retention, and selection handoff.
- `docs/LOCAL_LIBRARY_RANKING.md` documents normalization, match classes, routing, Norway in a Nutshell cross-type compatibility, and duplicate-preserving tie-breaking.
- The retired Python `calculator/fetch_lines.py` and `calculator/grid_autocomplete.py` APIs are not supported compatibility surfaces; they belonged to the replaced Streamlit data-editor workflow and were removed.

## Excel contract

The bundled `Calculation-template-Mal.xlsx` is the visual and structural source of truth. Export:

1. Builds one immutable export plan from Calculator state and currency rates.
2. Applies that plan through the fast XLSX-package renderer used by production downloads.
3. Generates validated package cell changes before worksheet XML mutation.
4. Rewrites only approved cells in `Curr` and `Kalk`, plus explicit workbook recalculation metadata.
5. Clones the exact XLSX ZIP package while preserving part order and metadata.
6. Leaves all other package parts byte-for-byte unchanged.
7. Restores canonical formulas while retaining explicit user overrides.
8. Reuses unchanged package bytes through a bounded, template-aware in-process cache.
9. Stages one browser-ready base64 workbook payload for direct component download; cloud project persistence is a separate workflow.

Import preserves editable data, compatible A1 formulas, overrides, VAT values, currency rates, and Calculator-owned date relationships. Date-link metadata is internal and does not replace or hide the visible Excel date cells. Export → import → recalculate must preserve totals and linked/locked date ownership.

## Invariants

1. Save → reload → recalculate preserves totals.
2. Excel export visually and structurally matches the retained reference workbook.
3. Export → import → recalculate preserves the calculation.
4. Passenger count is dashboard-only and never changes row formulas.
5. Invalid expressions, missing rates, `NaN`, infinity, and circular references block save-sensitive actions.
6. Manual formula/rate overrides are explicit, persisted, and exported.
7. Project switching and local file reopening cannot silently discard unsaved calculator or currency-rate changes.
8. Browser and Python calculations match on reference, randomized, and A1 dependency vectors.
9. Margin shortcuts produce the selected GP percentage from actual net NOK cost, including supplier commission and overrides.
10. Project save/reload and Excel export/import preserve financial inputs, formulas, precision, and calculated results.
11. Changing the authoritative trip start shifts linked dates only; manually locked dates remain fixed through save, recovery, and Excel round-trips.
12. EUR is the primary dashboard presentation currency, while NOK remains the canonical formula and secondary audit currency.

## Financial and Excel export parity boundary

Browser submissions are parsed by a browser-specific canonical row boundary. Visible supplier commission remains a percentage-point input, while hidden formula overrides—including `gp_percent_override`—already use canonical Python/Excel units and are never rescaled on return.

`calculator/financial_projection.py` performs one immutable calculation pass and owns downstream financial decisions such as positive supplier-cost status and automatic versus manual sales price. `calculator/workbook_export_plan.py` maps that projection into deterministic workbook mutations. The fast package renderer and openpyxl compatibility renderer only write the plan; they do not calculate prices, exchange rates, commission, VAT, margin, chargeability, or sales-price mode.

The visible workbook area follows the final contentful Calculator row plus ten editable blank rows. Preallocated blank rows, generated row identifiers, default currencies, and hidden Local Library provenance do not extend the sheet. Deliberate formulas and non-default content do.

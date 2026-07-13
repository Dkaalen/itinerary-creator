# Calculator architecture

## Ownership

- `calculator/calculations.py` is the authoritative financial engine.
- `calculator_grid_component/frontend/js/calculator_grid_math.js` is the immediate browser preview and must stay parity-tested against Python.
- `calculator/formula_map.py` owns Excel formulas.
- `calculator/workbook_export.py` writes values and canonical formulas into the retained template.
- `calculator/state_serialization.py` owns calculator backup/schema migration.
- `app_modules/saved_project_calculator_state.py` is the project-persistence boundary.

## Browser workflow

The grid has two explicit modes:

- **Selection mode:** arrows move between cells; the first click on fetched or pre-filled data focuses the grid.
- **Edit mode:** click the active cell, double-click, press `F2`/`Enter`, or type; arrows move the caret.

Browser edits are saved to the project-scoped local draft immediately and synchronized to Streamlit after a short debounce. Save, export, generate, library navigation, and workspace navigation flush the latest state first.

## Invariants

1. Save → reload → recalculate preserves totals.
2. Excel export reopens successfully and uses the same formula contract.
3. Passenger count is dashboard-only and never changes row formulas.
4. Invalid expressions, missing rates, `NaN`, and infinity block save-sensitive actions.
5. Manual formula/rate overrides are explicit, persisted, and exported.
6. Project switching cannot silently discard unsaved calculator or currency-rate changes.

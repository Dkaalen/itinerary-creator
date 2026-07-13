# Calculator architecture

## Ownership

- `calculator/cell_formula_engine.py` is the authoritative financial engine and A1 dependency evaluator.
- `calculator/calculations.py` aggregates canonical row, total, and dashboard results.
- `calculator_grid_component/frontend/js/calculator_grid_math.js` is the immediate browser preview and is parity-tested against Python.
- `calculator/formula_map.py` owns canonical Excel formulas.
- `calculator/workbook_package_export.py` clones the retained reference XLSX package and changes only approved worksheet cells.
- `calculator/workbook_import.py` reads compatible calculation workbooks without rebuilding them.
- `calculator/state_serialization.py` owns JSON backup/schema migration.
- `app_modules/saved_project_calculator_state.py` is the cloud-project persistence boundary.

## Browser workflow

The grid has two explicit modes:

- **Selection mode:** arrows move between cells; the first click on fetched or pre-filled data focuses the grid.
- **Edit mode:** click the active cell, double-click, press `F2`/`Enter`, or type; arrows move the caret.

Browser edits are written to a project-scoped local draft and synchronized to Streamlit after a short debounce. A capped local recovery history stores meaningful committed versions. Save, export, generate, library navigation, and workspace navigation flush the latest state first.

A1 formulas support relative and absolute references, dependency recalculation, copy/fill translation, and circular-reference errors. Python and JavaScript are independently parity-tested.

## Excel contract

The bundled `Calculation-template-Mal.xlsx` is the visual and structural source of truth. Export:

1. Copies the exact XLSX ZIP package.
2. Rewrites only approved cells in `Curr` and `Kalk`.
3. Leaves all other package parts byte-for-byte unchanged.
4. Restores canonical formulas while retaining explicit user overrides.

Import preserves editable data, compatible A1 formulas, overrides, VAT values, and currency rates. Export → import → recalculate must preserve totals.

## Invariants

1. Save → reload → recalculate preserves totals.
2. Excel export visually and structurally matches the retained reference workbook.
3. Export → import → recalculate preserves the calculation.
4. Passenger count is dashboard-only and never changes row formulas.
5. Invalid expressions, missing rates, `NaN`, infinity, and circular references block save-sensitive actions.
6. Manual formula/rate overrides are explicit, persisted, and exported.
7. Project switching cannot silently discard unsaved calculator or currency-rate changes.
8. Browser and Python calculations match on reference, randomized, and A1 dependency vectors.

# Project reconstruction ownership

Project reconstruction is split into two explicit authorities.

## Calculator workspace

`app_modules/calculator_restore.py` owns replacement of the in-memory Calculator workspace.

All restore sources converge there:

- saved-project Calculator snapshots through `restore_calculator_snapshot_to_state()`
- local Excel and Calculator backup imports through `apply_calculator_upload_import()`
- browser draft/recovery actions through `apply_calculator_grid_result()`

Saved snapshots normalize their durable schema before restoration. Excel imports replace the workbook currency table. JSON backups and browser recovery preserve the active currency table when they do not contain rates. Replacing a rate table also removes stale per-currency widget keys.

## Saved itinerary workflow

`app_modules/saved_project_restore.py` owns replacement of generated itinerary workflow state and rebuilding of its preview artifacts.

`load_saved_project()` performs only these outer responsibilities:

1. coerce and validate the saved-project contract
2. select and clean `current_snapshot`
3. capture a transactional project-switch baseline
4. invoke the canonical restore authority
5. roll back the complete previous project if restoration fails

Reopening never reparses source text and never regenerates itinerary copy. The generated baseline is retained only as immutable history in the saved-project contract; it is not a reopen source.

## Duplication and cloud switching

Cloud duplication copies the durable saved-project payload under a new project identity. Opening either the source or duplicate then uses the same saved itinerary and Calculator restore authorities. Project identity is committed only after preview reconstruction succeeds.

## Browser recovery boundary

Browser recovery remains local to the Calculator component until the recovered rows are sent through the guarded component protocol. Once accepted, the recovered `CalculatorState` enters the same Calculator restore authority as workbook and saved-project restores. Browser-only recovery metadata is never promoted into a saved itinerary project.

## Baseline restoration

The disconnected future-only `saved_project_baseline_restore.py` helper was removed. There is no runtime action that can silently replace `current_snapshot` with `generated_baseline_snapshot`. A future visible baseline-restore feature must be designed as an explicit confirmed workflow and use the same canonical saved-project restore path.

# Project reconstruction ownership

Project reconstruction is split into two explicit authorities.

## Calculator workspace

`app_modules/calculator_restore.py` owns replacement of the in-memory Calculator workspace.

All restore sources converge there:

- saved-project Calculator snapshots through `restore_calculator_snapshot_to_state()`
- local Excel and Calculator backup imports through `request_calculator_upload_import()` and `apply_calculator_upload_import()`
- browser draft/recovery actions through `apply_calculator_grid_result()`

Saved snapshots normalize their durable schema before restoration. Excel imports replace the workbook currency table. JSON backups and browser recovery preserve the active currency table when they do not contain rates. Replacing a rate table also removes stale per-currency widget keys.

Local Calculator file reopening is a destructive reconstruction boundary. If the current cloud project differs from its saved Calculator snapshot, or a detached Calculator contains meaningful rows, the validated import is held in session state until the user chooses **Open file anyway**. The browser-grid Excel action supplies its latest row state to this check so edits that have not yet become the backend authority cannot bypass the confirmation. Cancelling leaves the current workspace unchanged; untouched starter rows and clean saved snapshots reopen without extra friction.

## Saved itinerary workflow

`app_modules/saved_project_restore.py` owns replacement of generated itinerary workflow state and rebuilding of its preview artifacts.

`load_saved_project()` performs only these outer responsibilities:

1. coerce and validate the saved-project contract
2. select and clean `current_snapshot`
3. capture a transactional project-switch baseline
4. invoke the canonical restore authority
5. roll back the complete previous project if restoration fails

Reopening never reparses source text and never regenerates itinerary copy. The generated baseline is retained only as immutable history in the saved-project contract; it is not a reopen source.

## Local backup identity boundary

A user-uploaded `.itinerary.json` backup is reconstructed through the same saved-project authority, but it is not treated as an instruction to reconnect to the project id embedded in the file. The JSON object is validated before any destructive action. When the current workspace contains pasted supplier text, generated itinerary edits, name/layout changes, or meaningful Calculator rows, the validated backup is held in session state until the user explicitly chooses **Open backup anyway**. Cancelling or closing the project manager leaves the current workspace unchanged. Clean workspaces open directly. Before confirmed reconstruction, the payload receives a fresh project id. After reconstruction succeeds, prior cloud save paths, Calculator/PDF file markers, cached cloud downloads, browser-recovery namespace state, and project-manager confirmations are cleared. The imported backup is therefore shown as unsaved and its next cloud save creates or updates only its fresh identity.

Cloud opens are different: `load_saved_project(..., project_id_override=...)` preserves the selected Supabase project id. A failed local backup reconstruction leaves the previous cloud project and all of its persistence markers unchanged.

## Duplication and cloud switching

Cloud duplication copies the durable saved-project payload under a new project identity. Opening either the source or duplicate then uses the same saved itinerary and Calculator restore authorities. Project identity is committed only after preview reconstruction succeeds.

## Browser recovery boundary

Browser recovery remains local to the Calculator component until the recovered rows are sent through the guarded component protocol. Once accepted, the recovered `CalculatorState` enters the same Calculator restore authority as workbook and saved-project restores. Browser-only recovery metadata is never promoted into a saved itinerary project.

## Baseline restoration

The disconnected future-only `saved_project_baseline_restore.py` helper was removed. There is no runtime action that can silently replace `current_snapshot` with `generated_baseline_snapshot`. A future visible baseline-restore feature must be designed as an explicit confirmed workflow and use the same canonical saved-project restore path.

## Cloud project manager boundary

The Open project manager reads a bounded Supabase page through `list_cloud_itinerary_page()`. Search, sort, limit, and offset are applied by the repository, with a one-row lookahead used only to enable Next navigation. The UI renders at most twelve project rows inside a fixed-height scroll surface.

Project rows contain metadata, the primary Open action, and one compact action menu. Rename and delete forms are owned by the single selected-project detail panel. Calculator file records are queried only for that selected project, so listing projects does not create an N+1 file-query pattern. Opening a cloud project or local backup is confirmation-gated when the current workspace contains changed saved-project rows/edits, pasted supplier text, name/layout changes, or meaningful rows in a detached local Calculator; empty starter rows and otherwise clean workspaces do not trigger that warning. Open, rename, duplicate, delete, reconstruction, session cleanup, and rollback continue to use their existing transactional authorities.

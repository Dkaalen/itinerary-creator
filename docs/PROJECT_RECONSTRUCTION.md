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

Browser recovery remains in the bounded app-owned IndexedDB store and local to the Calculator component until the recovered rows are sent through the guarded component protocol. Once accepted, the recovered `CalculatorState` enters the same Calculator restore authority as workbook and saved-project restores. Browser-only recovery metadata is never promoted into a saved itinerary project.

## Rerun performance and dirty-state ownership

Supplier preview parsing is owned by `app_modules/supplier_preview_cache.py` and keyed by the exact raw supplier-text signature. The input preview and generation action share the same parsed rows and isolated parser diagnostics, so generation does not parse unchanged input a second time. The cache is cleared at every hard project boundary and reseeded from the newly generated or restored canonical rows; an older project can therefore never supply rows to a newer project merely because the raw source text matches. When Project Explorer is open, uncached supplier parsing is deferred until the Explorer closes.

Saved-project dirty detection is owned by `app_modules/project_workspace_revision.py`. Canonical component hashes are rebuilt once after a workspace mutation and reused on ordinary Streamlit reruns. Successful save/open operations store matching persisted signatures. Failed save and failed open rollback restore the prior revision, current signature cache and persisted signature baseline together with the rest of the project state. Plain mappings without revision ownership continue to use exact uncached comparison semantics for external callers and tests.

## Baseline restoration

The disconnected future-only `saved_project_baseline_restore.py` helper was removed. There is no runtime action that can silently replace `current_snapshot` with `generated_baseline_snapshot`. A future visible baseline-restore feature must be designed as an explicit confirmed workflow and use the same canonical saved-project restore path.

## Cloud project manager boundary

The Open project manager performs one cached capability probe for the optional organization schema, then reads exactly one supported Supabase list path. A legacy schema receives only name/date controls; owner and folder controls are not rendered. A migrated schema keeps search, sort, limit, offset, owner and folder filtering server-owned. Project pages and folder options use a short repository cache that is invalidated by local mutations and expires quickly enough to surface changes made by Dennis, Vipin or Christer. The toolbar action only changes visibility; Project Explorer itself is rendered after the toolbar at full page width.

The saved-project table is a dedicated browser component. Checkbox changes, the selection count and clear state remain in the browser and do not rerun Streamlit. The component submits durable project IDs only when the user explicitly reviews the selection or changes page. A tab-session namespace preserves the exact IDs across reruns, sorting and paging without allowing row positions or a previous Streamlit session to transfer selection to another record. Server list revisions reset stale browser selection after mutations.

Open, rename, duplicate and delete actions belong to the reviewed selection rather than every project row. A delete request stores one immutable confirmation token bound to the exact ordered project IDs and current list revision. The token is consumed once before deletion; changed selections, stale lists and replayed confirmations are rejected. Permanent deletion fetches registered files for the whole bounded selection, deletes Storage objects in bounded batches, and deletes only safely cleaned project records in bounded database batches. Missing records are idempotently complete. Successful deletions are removed from the selection, while Storage or database failures remain selected with exact retry ownership. Calculator file records are queried only for one reviewed project, so listing projects does not create an N+1 file-query pattern. Opening a cloud project or local backup remains confirmation-gated when the current workspace contains meaningful unsaved work.

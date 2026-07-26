# Session-state ownership

Cross-workflow Streamlit state uses one key registry and several responsibility-specific transition authorities:

- `app_modules/session_state_keys.py` owns shared key names and route/stage values.
- `app_modules/workflow_navigation.py` owns application routes, stage normalization, and visible-stage resolution.
- `app_modules/calculator_lifecycle.py` owns Calculator import and generation transitions.
- `app_modules/project_session_transitions.py` owns transactional project open, switch, save-failure, duplicate, and delete state.
- `app_modules/render_lifecycle.py` owns PDF/render invalidation.
- `app_modules/image_projection_state.py` projects committed itinerary state for image matching without mutating it.
- `app_modules/workflow_state.py` owns workflow defaults, project reset, and plain session snapshots only.

Domain modules may still own private or transient keys, but they must not repeat the protected cross-workflow literals.

## Transition ownership

| Workflow | Authority |
|---|---|
| Application route or workflow stage | `workflow_navigation.py` |
| Open or return to Calculator | `calculator_navigation.py` calling `workflow_navigation.py` |
| Import local Calculator workbook | `calculator_lifecycle.begin_local_calculator_import` |
| Generate from Calculator | `calculator_lifecycle.complete_calculator_generation` / `fail_calculator_generation` |
| Open or switch saved project | `project_session_transitions.capture_project_switch_baseline`, `complete_saved_project_open`, `restore_project_switch_baseline` |
| Duplicate cloud project | `project_session_transitions.complete_project_duplicate` |
| Delete cloud project | `project_session_transitions.complete_project_delete` |
| Failed cloud save | `project_session_transitions.record_failed_save` |
| PDF invalidation after content changes | `render_lifecycle.mark_pdf_dirty` |
| Image-matching row projection | `image_projection_state.image_grouped_days_from_state` |

Saved-project opening is transactional for the tracked workflow, Calculator, PDF, render-context, and identity keys. A validation failure does not change the active project, and a rebuild exception restores the previous tracked state.

## Calculator page boundary

- `calculator_page.py` composes the Streamlit layout and browser component protocol.
- `calculator_action_policy.py` decides backend validation scope and whether browser rows can become the Python authority.
- `calculator_page_actions.py` executes accepted navigation, download, import, generation, and backup actions.

The page does not own project reconstruction, financial formulas, or Local Library search.

## Domain-specific authorities

- Calculator keys: `app_modules/calculator_state_keys.py`
- Active project id: `app_modules/project_identity.py`
- PDF artifacts: `app_modules/pdf_artifact_state.py`
- Project-browser confirmation keys: `app_modules/project_browser_state.py`
- Visual-editor state: `visual_editor_component/*`

New cross-module state must be added to the shared registry before it is used by more than one workflow owner.

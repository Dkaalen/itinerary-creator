# Session-state ownership

Cross-workflow Streamlit state uses two dependency-free authorities:

- `app_modules/session_state_keys.py` owns shared key names and route/stage values.
- `app_modules/session_transitions.py` owns state changes that cross workflow boundaries.

Domain modules may still own private/transient keys, but they must not repeat the protected cross-workflow literals.

## Transition ownership

| Workflow | Authority |
|---|---|
| Open or return to Calculator | `calculator_navigation.py` calling `session_transitions` |
| Import local Calculator workbook | `begin_local_calculator_import` |
| Generate from Calculator | `complete_calculator_generation` / `fail_calculator_generation` |
| Open or switch saved project | `capture_project_switch_baseline`, `complete_saved_project_open`, `restore_project_switch_baseline` |
| Duplicate cloud project | `complete_project_duplicate` |
| Delete cloud project | `complete_project_delete` |
| Failed cloud save | `record_failed_save` |
| Workflow stage changes | `transition_workflow_stage` through `workflow_state.set_workflow_stage` |

Saved-project opening is transactional for the tracked workflow, Calculator, PDF, render-context, and identity keys. A validation failure does not change the active project, and a rebuild exception restores the previous tracked state.

## Domain-specific authorities

- Calculator keys: `app_modules/calculator_state_keys.py`
- Active project id: `app_modules/project_identity.py`
- PDF artifacts: `app_modules/pdf_artifact_state.py`
- Project-browser confirmation keys: `app_modules/project_browser_state.py`
- Visual-editor state: `visual_editor_component/*`

New cross-module state must be added to the shared registry before it is used by more than one workflow owner.

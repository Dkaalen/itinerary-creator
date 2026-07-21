"""Explicit state transitions across Calculator and saved-project workflows."""

from __future__ import annotations

from collections.abc import MutableMapping
from copy import deepcopy
from typing import Any, Mapping

from app_modules.session_state_keys import (
    ACTIVE_APP_PAGE_KEY,
    ACTIVE_SAVED_PROJECT_KEY,
    APP_STAGE_KEY,
    CALCULATOR_PAGE,
    ITINERARY_NAME_KEY,
    LOCAL_LIBRARY_PAGE,
    OPEN_PROJECT_BROWSER_VISIBLE_KEY,
    PROJECT_STORAGE_BROWSER_SUCCESS_KEY,
    PROJECT_STORAGE_DELETE_CLEANUP_WARNING_KEY,
    PROJECT_STORAGE_LAST_ERROR_DETAIL_KEY,
    PROJECT_STORAGE_LAST_ERROR_KEY,
    WORKFLOW_PAGE,
    WORKFLOW_STAGES,
)


_MISSING = object()


def _copy_state_value(value: Any) -> Any:
    try:
        return deepcopy(value)
    except Exception:
        return value


def _project_switch_keys(state: Mapping[str, Any]) -> tuple[str, ...]:
    from app_modules.calculator_state_keys import (
        CALCULATOR_DRAFT_NAMESPACE_KEY,
        CALCULATOR_ITINERARY_NAME_SYNC_REQUIRED_KEY,
        CALCULATOR_READY_DOWNLOAD_KEY,
        CALCULATOR_RETURN_AVAILABLE_KEY,
        CALCULATOR_STATE_KEY,
        CURRENCY_RATES_STATE_KEY,
    )
    from app_modules.pdf_artifact_state import PDF_ARTIFACT_KEYS
    from app_modules.workflow_transients import PROJECT_BOUNDARY_TRANSIENT_KEYS
    from app_modules.session_state_keys import (
        ACTIVE_PROJECT_STORAGE_ID_KEY,
        ACTIVE_SAVED_PROJECT_ID_KEY,
        DAY_PAGE_LAYOUT_KEY,
        DETAIL_LEVEL_KEY,
        HTML_PATH_KEY,
        ITINERARY_HTML_KEY,
        ITINERARY_NAME_INPUT_KEY,
        ITINERARY_VALIDATION_REPORT_KEY,
        LAST_GENERATED_RAW_TEXT_KEY,
        OUTPUT_EDITS_KEY,
        PARSED_ROWS_KEY,
        PARSER_DIAGNOSTICS_KEY,
        PRESENTATION_LANGUAGE_KEY,
        PREVIEW_SIGNATURE_KEY,
        RAW_TEXT_INPUT_KEY,
        STRUCTURED_INPUT_REVIEW_KEY,
        TONE_PRESET_KEY,
    )

    keys = {
        ACTIVE_APP_PAGE_KEY,
        APP_STAGE_KEY,
        ACTIVE_SAVED_PROJECT_KEY,
        ACTIVE_PROJECT_STORAGE_ID_KEY,
        ACTIVE_SAVED_PROJECT_ID_KEY,
        CALCULATOR_STATE_KEY,
        CURRENCY_RATES_STATE_KEY,
        CALCULATOR_DRAFT_NAMESPACE_KEY,
        CALCULATOR_ITINERARY_NAME_SYNC_REQUIRED_KEY,
        CALCULATOR_READY_DOWNLOAD_KEY,
        CALCULATOR_RETURN_AVAILABLE_KEY,
        PARSED_ROWS_KEY,
        OUTPUT_EDITS_KEY,
        RAW_TEXT_INPUT_KEY,
        LAST_GENERATED_RAW_TEXT_KEY,
        ITINERARY_HTML_KEY,
        HTML_PATH_KEY,
        PREVIEW_SIGNATURE_KEY,
        ITINERARY_VALIDATION_REPORT_KEY,
        PARSER_DIAGNOSTICS_KEY,
        STRUCTURED_INPUT_REVIEW_KEY,
        ITINERARY_NAME_KEY,
        ITINERARY_NAME_INPUT_KEY,
        PRESENTATION_LANGUAGE_KEY,
        TONE_PRESET_KEY,
        DETAIL_LEVEL_KEY,
        DAY_PAGE_LAYOUT_KEY,
        OPEN_PROJECT_BROWSER_VISIBLE_KEY,
        *PDF_ARTIFACT_KEYS,
        *PROJECT_BOUNDARY_TRANSIENT_KEYS,
    }
    for key in state.keys():
        text = str(key)
        if text.startswith(("calculator_currency_rate_", "_preview_render_context")):
            keys.add(text)
    return tuple(sorted(keys))


def capture_project_switch_baseline(state: Mapping[str, Any]) -> dict[str, Any]:
    """Capture keys that can change while reopening another project."""

    return {
        key: _copy_state_value(state[key]) if key in state else _MISSING
        for key in _project_switch_keys(state)
    }


def restore_project_switch_baseline(state: MutableMapping[str, Any], baseline: Mapping[str, Any]) -> None:
    """Restore the previous project after a failed open/rebuild operation."""

    tracked_keys = set(_project_switch_keys(state)) | set(baseline.keys())
    for key in tracked_keys:
        value = baseline.get(key, _MISSING)
        if value is _MISSING:
            state.pop(key, None)
        else:
            state[key] = _copy_state_value(value)


def normalize_workflow_stage(stage: object) -> str:
    value = str(stage or "input")
    return value if value in WORKFLOW_STAGES else "input"


def route_to_calculator(state: MutableMapping[str, Any]) -> None:
    state[ACTIVE_APP_PAGE_KEY] = CALCULATOR_PAGE


def return_to_calculator(state: MutableMapping[str, Any]) -> None:
    """Return from itinerary workflow to the preserved Calculator workspace."""

    route_to_calculator(state)


def route_to_local_library(state: MutableMapping[str, Any]) -> None:
    state[ACTIVE_APP_PAGE_KEY] = LOCAL_LIBRARY_PAGE


def route_to_workflow(state: MutableMapping[str, Any]) -> None:
    state[ACTIVE_APP_PAGE_KEY] = WORKFLOW_PAGE


def transition_workflow_stage(state: MutableMapping[str, Any], stage: object) -> str:
    normalized = normalize_workflow_stage(stage)
    state[APP_STAGE_KEY] = normalized
    return normalized


def begin_local_calculator_import(state: MutableMapping[str, Any]) -> None:
    """Detach an imported workbook from cloud identity while keeping Calculator active."""

    from app_modules.calculator_state_keys import CALCULATOR_RETURN_AVAILABLE_KEY
    from app_modules.project_session_cleanup import clear_active_cloud_project_session

    clear_active_cloud_project_session(state)
    state.pop(CALCULATOR_RETURN_AVAILABLE_KEY, None)
    route_to_calculator(state)


def complete_calculator_generation(state: MutableMapping[str, Any]) -> None:
    from app_modules.calculator_state_keys import CALCULATOR_RETURN_AVAILABLE_KEY

    state[CALCULATOR_RETURN_AVAILABLE_KEY] = True
    route_to_workflow(state)


def fail_calculator_generation(state: MutableMapping[str, Any], previous_stage: object) -> str:
    """Keep Calculator active and restore the prior valid workflow stage."""

    route_to_calculator(state)
    return transition_workflow_stage(state, previous_stage)


def complete_saved_project_open(
    state: MutableMapping[str, Any],
    *,
    project_payload: Mapping[str, Any],
    project_id: object,
) -> None:
    """Commit one coherent active-project identity after a successful open."""

    from app_modules.project_identity import set_active_project_id

    state[ACTIVE_SAVED_PROJECT_KEY] = deepcopy(dict(project_payload))
    set_active_project_id(state, project_id)
    route_to_workflow(state)
    state[OPEN_PROJECT_BROWSER_VISIBLE_KEY] = False


def complete_project_duplicate(state: MutableMapping[str, Any], *, name: object) -> None:
    state[PROJECT_STORAGE_BROWSER_SUCCESS_KEY] = f"Created {str(name or 'Untitled itinerary')}."


def complete_project_delete(
    state: MutableMapping[str, Any],
    *,
    project_id: object,
    name: object,
    storage_files_deleted: bool,
) -> None:
    """Apply session cleanup and browser messages after a successful deletion."""

    from app_modules.project_browser_state import clear_delete_confirmation
    from app_modules.project_delete_cleanup import clear_deleted_project_from_session

    clear_deleted_project_from_session(state, str(project_id or ""))
    clear_delete_confirmation(state)
    if not storage_files_deleted:
        state[PROJECT_STORAGE_DELETE_CLEANUP_WARNING_KEY] = (
            "Project record was deleted, but one or more stored files could not be removed automatically."
        )
    state[PROJECT_STORAGE_BROWSER_SUCCESS_KEY] = f"Deleted {str(name or 'project')}."


def record_failed_save(
    state: MutableMapping[str, Any],
    *,
    baseline: Mapping[str, Any] | None = None,
    user_message: object = "",
    technical_detail: object = "",
) -> None:
    """Rollback save-time identity mutations and expose one coherent failure state."""

    if baseline is not None:
        from app_modules.project_save_rollback import restore_project_save_baseline

        restore_project_save_baseline(state, dict(baseline))
    state[PROJECT_STORAGE_LAST_ERROR_KEY] = str(user_message or "Project could not be saved.")
    detail = " ".join(str(technical_detail or "").split())[:500]
    if detail:
        state[PROJECT_STORAGE_LAST_ERROR_DETAIL_KEY] = detail
    else:
        state.pop(PROJECT_STORAGE_LAST_ERROR_DETAIL_KEY, None)


def clear_failed_save(state: MutableMapping[str, Any]) -> None:
    state.pop(PROJECT_STORAGE_LAST_ERROR_KEY, None)
    state.pop(PROJECT_STORAGE_LAST_ERROR_DETAIL_KEY, None)


def prepare_project_switch(state: MutableMapping[str, Any]) -> None:
    """Clear browser confirmations before replacing the active project."""

    from app_modules.project_browser_state import (
        clear_delete_confirmation,
        clear_file_delete_confirmation,
        clear_open_candidate,
        clear_rename_candidate,
    )

    clear_delete_confirmation(state)
    clear_file_delete_confirmation(state)
    clear_open_candidate(state)
    clear_rename_candidate(state)


__all__ = [
    "begin_local_calculator_import",
    "capture_project_switch_baseline",
    "clear_failed_save",
    "complete_calculator_generation",
    "complete_project_delete",
    "complete_project_duplicate",
    "complete_saved_project_open",
    "fail_calculator_generation",
    "normalize_workflow_stage",
    "prepare_project_switch",
    "record_failed_save",
    "restore_project_switch_baseline",
    "return_to_calculator",
    "route_to_calculator",
    "route_to_local_library",
    "route_to_workflow",
    "transition_workflow_stage",
]

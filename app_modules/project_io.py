import json
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Any
from uuid import uuid4

import streamlit as st

from app_modules.debug_mode import is_debug_mode
from app_modules.preview_rebuild import rebuild_current_preview_for_state
from app_modules.project_browser_state import remember_selected_project
from app_modules.project_identity import project_payload_with_id
from app_modules.project_session_cleanup import clear_cloud_project_persistence_markers
from app_modules.project_unsaved_state import active_project_has_unsaved_changes
from app_modules.saved_project_constants import SAVED_PROJECT_KIND
from app_modules.saved_project_serialization import saved_project_from_dict
from app_modules.saved_project_validation import SavedProjectError
from app_modules.session_state_keys import PENDING_PROJECT_BACKUP_IMPORT_KEY
from app_modules.session_transitions import prepare_project_switch
from app_modules.validation_gate import (
    block_generation,
    render_blocking_issues,
    render_warning_issues,
)
from app_modules.workflow_actions import load_project, load_saved_project
from app_modules.workflow_state import (
    ensure_workflow_defaults,
    reset_workflow_state,
)


@dataclass(frozen=True)
class PendingProjectJsonImport:
    """One validated JSON object awaiting destructive-open confirmation."""

    payload: dict[str, Any]
    filename: str
    require_saved_project: bool


def initialise_state():
    ensure_workflow_defaults(st.session_state)


def load_project_json(uploaded_file, *, require_saved_project: bool = False) -> bool:
    """Open one project JSON immediately through the supported reconstruction path."""

    try:
        data = _read_project_json(uploaded_file)
    except Exception as error:
        return _report_project_open_error(error)
    return _load_project_data(data, require_saved_project=require_saved_project)


def request_project_json_import(uploaded_file, *, require_saved_project: bool = False) -> bool | None:
    """Open a clean workspace immediately or stage the backup behind confirmation."""

    try:
        data = _read_project_json(uploaded_file)
        _validate_requested_project_kind(data, require_saved_project=require_saved_project)
        _validate_saved_project_payload(data)
    except Exception as error:
        return _report_project_open_error(error)

    if active_project_has_unsaved_changes(st.session_state):
        st.session_state[PENDING_PROJECT_BACKUP_IMPORT_KEY] = PendingProjectJsonImport(
            payload=data,
            filename=str(getattr(uploaded_file, "name", "") or "itinerary backup").strip(),
            require_saved_project=bool(require_saved_project),
        )
        return None
    return _load_project_data(data, require_saved_project=require_saved_project)


def pending_project_json_import() -> PendingProjectJsonImport | None:
    pending = st.session_state.get(PENDING_PROJECT_BACKUP_IMPORT_KEY)
    return pending if isinstance(pending, PendingProjectJsonImport) else None


def cancel_pending_project_json_import() -> None:
    st.session_state.pop(PENDING_PROJECT_BACKUP_IMPORT_KEY, None)


def confirm_pending_project_json_import() -> bool:
    pending = pending_project_json_import()
    st.session_state.pop(PENDING_PROJECT_BACKUP_IMPORT_KEY, None)
    if pending is None:
        return False
    return _load_project_data(
        dict(pending.payload),
        require_saved_project=pending.require_saved_project,
    )


def _load_project_data(data: dict[str, Any], *, require_saved_project: bool) -> bool:
    try:
        _validate_requested_project_kind(data, require_saved_project=require_saved_project)
        _validate_saved_project_payload(data)

        opened_local_backup = data.get("kind") == SAVED_PROJECT_KIND
        if opened_local_backup:
            detached_payload = project_payload_with_id(data, str(uuid4()))
            result = load_saved_project(st.session_state, detached_payload)
        else:
            raw_text = data.get("raw_text", "")
            output_edits = data.get("output_edits", {})
            result = load_project(st.session_state, raw_text, output_edits)

        validation_report = (result.payload or {}).get("validation_report")
        if validation_report and validation_report.is_blocked:
            block_generation(validation_report)
            render_blocking_issues(validation_report)
            return False

        if validation_report:
            render_warning_issues(validation_report)
        if result.ok:
            if opened_local_backup:
                clear_cloud_project_persistence_markers(st.session_state)
                prepare_project_switch(st.session_state)
                remember_selected_project(st.session_state, "")
                st.success("Backup opened as a new unsaved project.")
            else:
                st.success(result.message or "Editable project loaded.")
        else:
            st.error(result.message or "The project file could not be loaded.")
        return bool(result.ok)
    except Exception as error:
        return _report_project_open_error(error)


def _validate_requested_project_kind(data: dict[str, Any], *, require_saved_project: bool) -> None:
    if require_saved_project and data.get("kind") != SAVED_PROJECT_KIND:
        raise SavedProjectError("Please upload a saved itinerary project file.")


def _validate_saved_project_payload(data: dict[str, Any]) -> None:
    if data.get("kind") == SAVED_PROJECT_KIND:
        saved_project_from_dict(data)


def _report_project_open_error(error: Exception) -> bool:
    if isinstance(error, SavedProjectError):
        st.error(f"The project file could not be opened: {error}")
        return False
    if isinstance(error, (UnicodeDecodeError, JSONDecodeError, ValueError, TypeError)):
        st.error("The project file is not valid JSON.")
        if is_debug_mode(st.session_state):
            st.exception(error)
        return False
    st.error("The project file could not be loaded.")
    if is_debug_mode(st.session_state):
        st.exception(error)
    return False


def _read_project_json(uploaded_file) -> dict[str, Any]:
    if hasattr(uploaded_file, "getvalue"):
        content = bytes(uploaded_file.getvalue())
    elif hasattr(uploaded_file, "read"):
        content = bytes(uploaded_file.read())
    else:
        raise TypeError("Project upload must provide bytes.")
    data = json.loads(content.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Project JSON must contain an object.")
    return data


def reset_project_state(clear_raw_text=True):
    """Clear the current project and return the app to a clean generation state."""
    reset_workflow_state(st.session_state, clear_raw_text=clear_raw_text)


def rebuild_current_preview(mark_pdf_dirty=True, force=False, save_html=True):
    """Compatibility wrapper for rebuilding the current Streamlit preview."""

    return rebuild_current_preview_for_state(
        st.session_state,
        mark_pdf_dirty=mark_pdf_dirty,
        force=force,
        save_html=save_html,
    )


__all__ = [
    "PendingProjectJsonImport",
    "cancel_pending_project_json_import",
    "confirm_pending_project_json_import",
    "initialise_state",
    "load_project_json",
    "pending_project_json_import",
    "rebuild_current_preview",
    "request_project_json_import",
    "reset_project_state",
]

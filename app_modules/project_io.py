import json
from json import JSONDecodeError

import streamlit as st

from app_modules.workflow_state import (
    ensure_workflow_defaults,
    reset_workflow_state,
)
from app_modules.debug_mode import is_debug_mode
from app_modules.saved_project_constants import SAVED_PROJECT_KIND
from app_modules.saved_project_validation import SavedProjectError
from app_modules.workflow_actions import load_project, load_saved_project
from app_modules.preview_rebuild import rebuild_current_preview_for_state
from app_modules.validation_gate import (
    block_generation,
    render_blocking_issues,
    render_warning_issues,
)


def initialise_state():
    ensure_workflow_defaults(st.session_state)


def load_project_json(uploaded_file, *, require_saved_project: bool = False) -> bool:
    try:
        data = _read_project_json(uploaded_file)
        if require_saved_project and data.get("kind") != SAVED_PROJECT_KIND:
            raise SavedProjectError("Please upload a saved itinerary project file.")

        if data.get("kind") == SAVED_PROJECT_KIND:
            result = load_saved_project(st.session_state, data)
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
            st.success(result.message or "Editable project loaded.")
        else:
            st.error(result.message or "The project file could not be loaded.")
        return bool(result.ok)
    except SavedProjectError as error:
        st.error(f"The project file could not be opened: {error}")
        return False
    except (UnicodeDecodeError, JSONDecodeError, ValueError) as error:
        st.error("The project file is not valid JSON.")
        if is_debug_mode(st.session_state):
            st.exception(error)
        return False
    except Exception as error:
        st.error("The project file could not be loaded.")
        if is_debug_mode(st.session_state):
            st.exception(error)
        return False


def _read_project_json(uploaded_file) -> dict:
    data = json.loads(uploaded_file.read().decode("utf-8"))
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

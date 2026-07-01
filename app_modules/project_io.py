import json
from json import JSONDecodeError

import streamlit as st

from itinerary_generation.common import group_rows_by_day
from ui.export_files import save_html_file
from ui.render_cache import make_render_signature
from ui.output_edits import apply_output_edits
from app_modules.workflow_state import (
    ensure_workflow_defaults,
    mark_pdf_dirty as mark_pdf_dirty_state,
    reset_workflow_state,
)
from app_modules.debug_mode import is_debug_mode
from app_modules.saved_project_constants import SAVED_PROJECT_KIND
from app_modules.saved_project_validation import SavedProjectError
from app_modules.workflow_actions import load_project, load_saved_project
from app_modules.itinerary_html import build_itinerary_html_from_context
from app_modules.itinerary_render_context import build_itinerary_render_context
from app_modules.render_context_cache import store_render_context
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
    """Ensure the preview/HTML matches the current editable project state.

    Streamlit reruns frequently while the user scrolls or clicks buttons. The
    render signature lets us skip the expensive HTML rebuild unless the actual
    itinerary content changed.
    """
    parsed_rows = st.session_state.get("parsed_rows", [])
    output_edits = st.session_state.get("output_edits", {})

    if not parsed_rows or not output_edits:
        return False

    render_signature = make_render_signature(parsed_rows, output_edits)
    cached_signature = st.session_state.get("preview_signature")
    has_html = bool(st.session_state.get("itinerary_html", ""))

    if not force and has_html and cached_signature == render_signature:
        if save_html and not st.session_state.get("html_path"):
            st.session_state.html_path = save_html_file(st.session_state.itinerary_html)
        return True

    edited_rows = apply_output_edits(parsed_rows, output_edits)
    edited_grouped_days = group_rows_by_day(edited_rows)
    render_context = build_itinerary_render_context(edited_rows, edited_grouped_days, output_edits)
    rebuilt_html = build_itinerary_html_from_context(render_context)

    html_changed = rebuilt_html != st.session_state.get("itinerary_html", "")
    st.session_state.itinerary_html = rebuilt_html
    st.session_state.preview_signature = render_signature
    store_render_context(st.session_state, signature=render_signature, context=render_context)

    if mark_pdf_dirty and html_changed:
        mark_pdf_dirty_state(st.session_state, status="Needs refresh")

    if save_html:
        st.session_state.html_path = save_html_file(st.session_state.itinerary_html)
    return True

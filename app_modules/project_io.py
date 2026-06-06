import json

import streamlit as st

from itinerary_generation.common import group_rows_by_day
from ui.export_files import save_html_file
from ui.render_cache import make_render_signature
from ui.output_edits import (
    apply_output_edits,
    make_output_edit_state,
    refresh_generated_text_for_detail_level,
)
from layout_policy import DEFAULT_DAY_PAGE_LAYOUT
from app_modules.workflow_state import (
    clear_pdf_artifacts,
    ensure_workflow_defaults,
    mark_pdf_dirty as mark_pdf_dirty_state,
    reset_workflow_state,
    set_workflow_stage,
)
from app_modules.parse_workflow import parse_and_normalize_itinerary
from app_modules.itinerary_html import build_itinerary_html
from app_modules.validation_gate import (
    block_generation,
    render_blocking_issues,
    render_warning_issues,
    validate_for_generation,
)


def initialise_state():
    ensure_workflow_defaults(st.session_state)


def load_project_json(uploaded_file):
    try:
        data = json.loads(uploaded_file.read().decode("utf-8"))
        raw_text = data.get("raw_text", "")
        output_edits = data.get("output_edits", {})

        parsed_rows = parse_and_normalize_itinerary(raw_text)
        validation_report = validate_for_generation(parsed_rows)
        if validation_report.is_blocked:
            block_generation(validation_report)
            render_blocking_issues(validation_report)
            return

        grouped_days = group_rows_by_day(parsed_rows)

        st.session_state.parsed_rows = parsed_rows
        previous_detail = (output_edits or {}).get("detail_level", "Standard client itinerary")
        st.session_state.output_edits = output_edits or make_output_edit_state(parsed_rows, grouped_days)
        st.session_state.output_edits = refresh_generated_text_for_detail_level(
            parsed_rows,
            st.session_state.output_edits,
            previous_detail,
            "Rich descriptive",
        )
        st.session_state.detail_level = "Rich descriptive"
        st.session_state.output_edits["detail_level"] = "Rich descriptive"
        st.session_state.day_page_layout = st.session_state.output_edits.get("day_page_layout", st.session_state.get("day_page_layout", DEFAULT_DAY_PAGE_LAYOUT))
        st.session_state.last_generated_raw_text = raw_text
        clear_pdf_artifacts(st.session_state, status="Not created")

        edited_rows = apply_output_edits(parsed_rows, st.session_state.output_edits)
        edited_grouped_days = group_rows_by_day(edited_rows)
        st.session_state.itinerary_html = build_itinerary_html(edited_rows, edited_grouped_days, st.session_state.output_edits)
        st.session_state.preview_signature = make_render_signature(parsed_rows, st.session_state.output_edits)
        st.session_state.html_path = save_html_file(st.session_state.itinerary_html)
        clear_pdf_artifacts(st.session_state, status="Not created")
        st.session_state.raw_text_input = raw_text
        set_workflow_stage(st.session_state, "pictures" if st.session_state.output_edits.get("pictures_added") else "edit")

        render_warning_issues(validation_report)
        st.success("Editable project loaded.")
    except Exception as error:
        st.error("The project JSON could not be loaded.")
        st.exception(error)


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
    rebuilt_html = build_itinerary_html(edited_rows, edited_grouped_days, output_edits)

    html_changed = rebuilt_html != st.session_state.get("itinerary_html", "")
    st.session_state.itinerary_html = rebuilt_html
    st.session_state.preview_signature = render_signature

    if mark_pdf_dirty and html_changed:
        mark_pdf_dirty_state(st.session_state, status="Needs refresh")

    if save_html:
        st.session_state.html_path = save_html_file(st.session_state.itinerary_html)
    return True

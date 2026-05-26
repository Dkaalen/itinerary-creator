import json

import streamlit as st

from itinerary_generation.common import group_rows_by_day
from ui.export_files import save_html_file
from ui.output_edits import (
    apply_output_edits,
    make_output_edit_state,
    refresh_generated_text_for_detail_level,
)
from layout_policy import DEFAULT_DAY_PAGE_LAYOUT
from app_modules.parse_workflow import parse_and_normalize_itinerary
from app_modules.itinerary_html import build_itinerary_html


def initialise_state():
    defaults = {
        "itinerary_html": "",
        "html_path": None,
        "pdf_bytes": None,
        "parsed_rows": [],
        "output_edits": {},
        "last_generated_raw_text": "",
        "parser_diagnostics": [],
        "pdf_status": "Not created",
        "detail_level": "Rich descriptive",
        "day_page_layout": "Smart compact pages",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def load_project_json(uploaded_file):
    try:
        data = json.loads(uploaded_file.read().decode("utf-8"))
        raw_text = data.get("raw_text", "")
        output_edits = data.get("output_edits", {})

        parsed_rows = parse_and_normalize_itinerary(raw_text)
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
        st.session_state.pdf_bytes = None

        edited_rows = apply_output_edits(parsed_rows, st.session_state.output_edits)
        edited_grouped_days = group_rows_by_day(edited_rows)
        st.session_state.itinerary_html = build_itinerary_html(edited_rows, edited_grouped_days, st.session_state.output_edits)
        st.session_state.html_path = save_html_file(st.session_state.itinerary_html)
        st.session_state.raw_text_input = raw_text

        st.success("Editable project loaded.")
    except Exception as error:
        st.error("The project JSON could not be loaded.")
        st.exception(error)


def reset_project_state(clear_raw_text=True):
    """Clear the current project and return the app to a clean generation state."""
    for key in [
        "itinerary_html",
        "html_path",
        "pdf_bytes",
        "parsed_rows",
        "output_edits",
        "last_generated_raw_text",
        "parser_diagnostics",
        "_last_visual_editor_result",
    ]:
        if key in st.session_state:
            del st.session_state[key]

    st.session_state.itinerary_html = ""
    st.session_state.html_path = None
    st.session_state.pdf_bytes = None
    st.session_state.parsed_rows = []
    st.session_state.output_edits = {}
    st.session_state.last_generated_raw_text = ""
    st.session_state.parser_diagnostics = []
    st.session_state.pdf_status = "Not created"

    if clear_raw_text:
        st.session_state.raw_text_input = ""


def rebuild_current_preview(mark_pdf_dirty=True):
    """Rebuild the preview/HTML from the current editable project state."""
    parsed_rows = st.session_state.get("parsed_rows", [])
    output_edits = st.session_state.get("output_edits", {})

    if not parsed_rows or not output_edits:
        return False

    edited_rows = apply_output_edits(parsed_rows, output_edits)
    edited_grouped_days = group_rows_by_day(edited_rows)
    rebuilt_html = build_itinerary_html(edited_rows, edited_grouped_days, output_edits)

    if rebuilt_html != st.session_state.get("itinerary_html", ""):
        if mark_pdf_dirty:
            st.session_state.pdf_bytes = None
            st.session_state.pdf_status = "Needs refresh"
        st.session_state.itinerary_html = rebuilt_html
    else:
        st.session_state.itinerary_html = rebuilt_html

    st.session_state.html_path = save_html_file(st.session_state.itinerary_html)
    return True

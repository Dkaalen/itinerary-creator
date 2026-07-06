from __future__ import annotations

import streamlit as st

from app_modules.app_header import _render_app_header, _stage_panel
from app_modules.calculator_navigation import open_calculator_page, open_local_library_page
from app_modules.debug_mode import is_debug_mode
from app_modules.input_workspace import (
    render_input_header,
    render_input_toolbar,
    render_source_label,
)
from app_modules.itinerary_name_state import sync_itinerary_name_from_input
from app_modules.itinerary_name_ui import render_itinerary_name_input
from app_modules.presentation_language import DEFAULT_PRESENTATION_LANGUAGE
from itinerary_generation.tone_presets import DEFAULT_TONE_PRESET
from app_modules.project_file_ui import render_open_project_file_action
from app_modules.project_io import load_project_json
from app_modules.validation_gate import block_generation, render_blocking_issues, render_warning_issues
from app_modules.workflow_actions import generate_itinerary
from app_modules.workflow_config import STAGE_COPY
from app_modules.workflow_state import set_workflow_stage
from ui.picture_workflow import pictures_are_added


def _set_stage(stage: str) -> None:
    set_workflow_stage(st.session_state, stage)


def _generate_itinerary(raw_text: str, output_brand: str = "agent") -> bool:
    sync_itinerary_name_from_input(st.session_state)
    st.session_state["requested_output_brand"] = output_brand
    st.session_state["presentation_language"] = DEFAULT_PRESENTATION_LANGUAGE
    st.session_state["tone_preset"] = DEFAULT_TONE_PRESET
    st.session_state["requested_presentation_language"] = DEFAULT_PRESENTATION_LANGUAGE
    st.session_state["requested_tone_preset"] = DEFAULT_TONE_PRESET
    result = generate_itinerary(st.session_state, raw_text)
    if not result.ok:
        validation_report = (result.payload or {}).get("validation_report")
        if validation_report is not None:
            block_generation(validation_report)
            render_blocking_issues(validation_report)
        return False
    return True


def _render_generation_messages() -> None:
    if not is_debug_mode(st.session_state):
        return
    from ui.input_review_panel import render_structured_input_review_panel

    render_structured_input_review_panel(
        st.session_state.get("parsed_rows", []),
        st.session_state.get("parser_diagnostics", []),
        st.session_state.get("structured_input_review"),
    )
    duplicate_count = st.session_state.get("generation_duplicate_count", 0)
    if duplicate_count:
        st.warning(f"Skipped approximately {duplicate_count} duplicate, continuation, or malformed row(s).")
    for warning in st.session_state.get("generation_overflow_warnings", []) or []:
        st.warning(warning)
    validation_report = st.session_state.get("itinerary_validation_report")
    if validation_report:
        render_warning_issues(validation_report)


def render_input_page(app_version: str) -> None:
    st.session_state["presentation_language"] = DEFAULT_PRESENTATION_LANGUAGE
    st.session_state["tone_preset"] = DEFAULT_TONE_PRESET

    _render_app_header(app_version, stage="input")
    _stage_panel(STAGE_COPY["input"]["panel_title"], STAGE_COPY["input"]["panel_text"])

    brand_col, calculator_col, library_col, project_col = st.columns(
        [0.50, 0.16, 0.16, 0.18],
        vertical_alignment="center",
    )
    with brand_col:
        render_input_toolbar()
    if calculator_col.button("Calculator", use_container_width=True, help="Build pricing rows before generating an itinerary."):
        open_calculator_page(st.session_state)
        st.rerun()
    if library_col.button("Local Library", use_container_width=True, help="Manage reusable calculator rows."):
        open_local_library_page(st.session_state)
        st.rerun()
    with project_col:
        render_open_project_file_action()

    render_input_header()
    render_itinerary_name_input()
    render_source_label()
    raw_text = st.text_area(
        "Supplier text",
        height=440,
        placeholder="Paste itinerary rows here…",
        key="raw_text_input",
        label_visibility="collapsed",
    )

    agent_col, customer_col, spacer_col = st.columns([0.26, 0.30, 0.44])
    generate_agent = agent_col.button("Generate agent itinerary", type="primary", use_container_width=True)
    generate_customer = customer_col.button("Generate customer itinerary", use_container_width=True)
    spacer_col.empty()
    if generate_agent or generate_customer:
        if not raw_text.strip():
            st.warning("Paste the supplier rows first, then generate the itinerary.")
            return
        output_brand = "booknordics_customer" if generate_customer else "agent"
        with st.spinner("Building your itinerary…"):
            generated = _generate_itinerary(raw_text, output_brand)
        if generated:
            _set_stage("edit")
            st.rerun()

    if is_debug_mode(st.session_state):
        with st.container(border=True):
            st.markdown("**Load legacy editable project JSON**")
            uploaded_project = st.file_uploader("Load legacy editable project JSON", type=["json"], label_visibility="collapsed")
            if uploaded_project is not None and st.button("Load legacy project", use_container_width=True):
                if load_project_json(uploaded_project):
                    _set_stage("pictures" if pictures_are_added(st.session_state.get("output_edits", {})) else "edit")
                    st.rerun()

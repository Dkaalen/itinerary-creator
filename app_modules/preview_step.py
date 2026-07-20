from __future__ import annotations

import streamlit as st

from app_modules.app_header import _render_app_header, _render_stage_actions, _stage_panel
from app_modules.add_pictures_cta import (
    add_pictures_apply_pending,
    add_pictures_apply_ready,
    maybe_rerun_after_editor_commit,
    render_add_pictures_cta,
)
from app_modules.generation_messages import render_generation_messages
from app_modules.calculator_navigation import render_return_to_calculator_button
from app_modules.project_io import rebuild_current_preview
from app_modules.workflow_config import STAGE_COPY
from itinerary_generation.common import group_rows_by_day
from ui.export_files import save_html_file
from ui.output_edits import apply_output_edits, mark_output_dirty
from ui.render_cache import make_render_signature
from visual_editor_component.editor_workflow import render_visual_editor


def _render_document_editor(*, pictures_active: bool) -> None:
    if not (st.session_state.get("parsed_rows") and st.session_state.get("output_edits")):
        return

    edited_rows = apply_output_edits(st.session_state.parsed_rows, st.session_state.output_edits)
    edited_grouped_days = group_rows_by_day(edited_rows)

    editor_applied = render_visual_editor(
        edited_rows,
        edited_grouped_days,
        st.session_state.output_edits,
        rebuild_preview=rebuild_current_preview,
        mark_dirty=mark_output_dirty,
    )
    if editor_applied:
        return

    render_signature = make_render_signature(st.session_state.parsed_rows, st.session_state.output_edits)
    preview_is_current = (
        bool(st.session_state.get("itinerary_html", ""))
        and st.session_state.get("preview_signature") == render_signature
    )
    if not preview_is_current:
        rebuild_current_preview(mark_pdf_dirty=True, force=True, save_html=True)
    elif not st.session_state.get("html_path"):
        st.session_state.html_path = save_html_file(st.session_state.itinerary_html)

def render_edit_page(app_version: str) -> None:
    _render_app_header(app_version, stage="edit")
    render_generation_messages(st.session_state)
    _render_stage_actions("edit")
    render_return_to_calculator_button()
    _stage_panel(STAGE_COPY["edit"]["panel_title"], STAGE_COPY["edit"]["panel_text"])

    was_waiting_for_apply = add_pictures_apply_pending()
    if not add_pictures_apply_ready():
        _render_document_editor(pictures_active=False)
        maybe_rerun_after_editor_commit(was_waiting_for_apply)

    render_add_pictures_cta()

from __future__ import annotations

from html import escape

import streamlit as st

from app_modules.project_file_ui import render_save_project_file_action
from app_modules.project_io import rebuild_current_preview, reset_project_state
from app_modules.workflow_config import STAGE_LABELS
from app_modules.workflow_shell import build_project_metrics, project_title
from app_modules.workflow_state import set_workflow_stage


def _stage_panel(title: str, body: str) -> None:
    """Render no large stage panel.

    The compact workspace shell carries orientation; page bodies should remain
    focused on the active work instead of repeating explanatory cards.
    """

    return None


def _render_top_nav(stage: str) -> None:
    """Render no large workflow navigation."""

    return None


def _render_app_header(app_version: str, *, stage: str) -> None:
    """Render a compact premium workspace shell when an itinerary exists."""

    session_state = getattr(st, "session_state", {})
    parsed_rows = session_state.get("parsed_rows") or []
    if not parsed_rows:
        return None

    output_edits = session_state.get("output_edits") or {}
    metrics = build_project_metrics(parsed_rows, output_edits)
    title = str(session_state.get("itinerary_name") or project_title(output_edits)).strip() or "New itinerary"
    stage_label = STAGE_LABELS.get(stage, str(stage).title())
    day_label = f"{metrics['days']} day" if metrics["days"] == 1 else f"{metrics['days']} days"
    saved_label = "Cloud saved" if session_state.get("project_storage_last_saved_snapshot_path") else "Unsaved changes"

    st.html(
        '<div class="workspace-shell">'
        '<div class="workspace-shell-main">'
        f'<span class="workspace-eyebrow">{escape(stage_label)}</span>'
        f'<strong>{escape(title)}</strong>'
        f'<span>{escape(day_label)} · {escape(saved_label)}</span>'
        '</div>'
        '</div>'
    )
    return None


def _render_stage_actions(stage: str) -> None:
    left, middle, right = st.columns([1, 1, 1])
    with left:
        if st.button("Start over", use_container_width=True):
            reset_project_state(clear_raw_text=True)
            set_workflow_stage(st.session_state, "input")
            st.rerun()
    with middle:
        if stage != "input":
            render_save_project_file_action(key_suffix=stage)
    with right:
        if stage != "input" and st.button("Refresh itinerary", use_container_width=True):
            rebuild_current_preview(mark_pdf_dirty=True, force=True, save_html=True)
            st.success("Itinerary refreshed.")
            st.rerun()

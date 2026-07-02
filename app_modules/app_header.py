from __future__ import annotations

import streamlit as st

from app_modules.project_file_ui import render_save_project_file_action
from app_modules.project_io import rebuild_current_preview, reset_project_state
from app_modules.workflow_state import set_workflow_stage


def _stage_panel(title: str, body: str) -> None:
    """Render no stage panel.

    Pages now behave as focused workspaces. The previous stage cards duplicated
    page context, consumed vertical space, and made the app feel like a landing
    page instead of a production tool.
    """

    return None


def _render_top_nav(stage: str) -> None:
    """Render no large workflow navigation."""

    return None


def _render_app_header(app_version: str, *, stage: str) -> None:
    """Render no persistent app header or route/status card."""

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

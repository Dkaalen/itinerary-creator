from __future__ import annotations

from html import escape

import streamlit as st

from app_modules.project_file_ui import render_save_project_file_action
from app_modules.project_io import rebuild_current_preview, reset_project_state
from app_modules.workflow_config import FLOW_STAGES, STAGE_COPY, STAGE_LABELS
from app_modules.workflow_shell import build_project_metrics, project_route_label, project_title
from app_modules.workflow_state import set_workflow_stage


def _stage_panel(title: str, body: str) -> None:
    st.html(
        '<div class="document-stage-panel">'
        f'<h2>{escape(title)}</h2>'
        f'<p>{escape(body)}</p>'
        '</div>'
    )

def _render_top_nav(stage: str) -> None:
    """Keep the old workflow-nav hook as a no-op.

    The app is now a working tool, not a landing page; the large stage header and
    route/status card were visually noisy and consumed too much vertical space.
    """

    return None


def _render_app_header(app_version: str, *, stage: str) -> None:
    """Render no persistent top header.

    Individual pages own their controls and status messages. This keeps the
    itinerary/calculator work area compact and removes the old hero/status card.
    """

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

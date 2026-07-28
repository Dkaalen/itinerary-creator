from __future__ import annotations

from html import escape

import streamlit as st

from app_modules.workflow_config import STAGE_LABELS
from app_modules.workflow_navigation import transition_workflow_stage
from app_modules.project_persistence_state import active_cloud_project_is_persisted, last_saved_project_baseline
from app_modules.project_unsaved_state import active_project_has_unsaved_changes
from app_modules.session_state_keys import (
    ITINERARY_NAME_KEY,
    OUTPUT_EDITS_KEY,
    PARSED_ROWS_KEY,
)


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
    parsed_rows = session_state.get(PARSED_ROWS_KEY) or []
    if not parsed_rows:
        return None

    from app_modules.workflow_shell import build_project_metrics, project_title

    output_edits = session_state.get(OUTPUT_EDITS_KEY) or {}
    metrics = build_project_metrics(parsed_rows, output_edits)
    title = str(session_state.get(ITINERARY_NAME_KEY) or project_title(output_edits)).strip() or "New itinerary"
    stage_label = STAGE_LABELS.get(stage, str(stage).title())
    day_label = f"{metrics['days']} day" if metrics["days"] == 1 else f"{metrics['days']} days"
    if not active_cloud_project_is_persisted(session_state):
        saved_label = "Not saved"
    elif active_project_has_unsaved_changes(session_state):
        saved_label = "Unsaved changes"
    else:
        baseline = last_saved_project_baseline(session_state) or {}
        metadata = baseline.get("metadata") if isinstance(baseline, dict) else {}
        saved_at = str((metadata or {}).get("updated_at") or "") if isinstance(metadata, dict) else ""
        saved_label = _saved_status_label(saved_at)

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



def _saved_status_label(value: object) -> str:
    from datetime import datetime, timezone

    text = str(value or "").strip()
    if not text:
        return "Saved"
    try:
        saved = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return "Saved"
    if saved.tzinfo is None:
        saved = saved.replace(tzinfo=timezone.utc)
    now = datetime.now(saved.tzinfo)
    if saved.date() == now.date():
        return f"Saved {saved.strftime('%H:%M')}"
    return "Saved"

def _render_stage_actions(stage: str) -> None:
    from app_modules.project_file_ui import render_save_project_file_action
    from app_modules.project_io import rebuild_current_preview, reset_project_state

    with st.container(key="workflow_stage_actions"):
        left, middle, right = st.columns([0.22, 0.56, 0.22], gap="small", vertical_alignment="top")
        with left:
            if st.button("Start over", use_container_width=True):
                reset_project_state(clear_raw_text=True)
                transition_workflow_stage(st.session_state, "input")
                st.rerun()
        with middle:
            if stage != "input":
                render_save_project_file_action(key_suffix=stage)
        with right:
            if stage != "input" and st.button("Refresh itinerary", use_container_width=True):
                rebuild_current_preview(mark_pdf_dirty=True, force=True, save_html=True)
                st.success("Itinerary refreshed.")
                st.rerun()

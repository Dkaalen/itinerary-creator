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
    current_index = FLOW_STAGES.index(stage)
    items = []
    for index, item in enumerate(FLOW_STAGES):
        status = "done" if index < current_index else "current" if item == stage else "locked"
        items.append(
            f'<div class="flow-nav-item flow-nav-{status}">'
            f'<span>{index + 1}</span><strong>{escape(STAGE_LABELS[item])}</strong>'
            f'</div>'
        )
    st.html(f'<div class="flow-nav" aria-label="Itinerary workflow">{"".join(items)}</div>')

def _render_app_header(app_version: str, *, stage: str) -> None:
    metrics = build_project_metrics(
        st.session_state.get("parsed_rows", []),
        st.session_state.get("output_edits", {}),
    )
    title = project_title(st.session_state.get("output_edits", {}), "Create itinerary")
    copy = STAGE_COPY[stage]
    headline = copy.get("headline") or title
    subtitle = copy["subtitle"]

    route = project_route_label(metrics)
    duration = f"{metrics['days']} days" if metrics["days"] else "Not generated yet"
    image_status = "Pictures added" if metrics["pictures_added"] else "Text only"
    pdf_status = str(st.session_state.get("pdf_status", "Not created") or "Not created")

    st.html(
        '<div class="luxury-hero">'
        '<div class="luxury-hero-main">'
        '<div class="hero-eyebrow">Itinerary App</div>'
        f'<h1>{escape(headline)}</h1>'
        f'<p>{escape(subtitle)}</p>'
        '</div>'
        '<div class="hero-summary-card">'
        f'<div><span>Route</span><strong>{escape(route)}</strong></div>'
        f'<div><span>Duration</span><strong>{escape(duration)}</strong></div>'
        f'<div><span>Imagery</span><strong>{escape(image_status)}</strong></div>'
        f'<div><span>PDF</span><strong>{escape(pdf_status)}</strong></div>'
        '</div>'
        '</div>'
        f'<div class="app-version-pill">Version {escape(str(app_version))}</div>'
    )
    _render_top_nav(stage)

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

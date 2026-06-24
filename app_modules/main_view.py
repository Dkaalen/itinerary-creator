from __future__ import annotations

# Split-source breadcrumbs for legacy source-contract tests:
# Create PDF applies pending page edits first; PDF already up to date -> workflow_config.py
# preview_signature; editor_applied -> preview_step.py

import streamlit as st

from app_modules.debug_tools import render_debug_tools
from app_modules.export_page import render_export_page
from app_modules.input_step import render_input_page
from app_modules.picture_step import render_picture_page
from app_modules.preview_step import (
    _activate_picture_stage,
    _add_pictures_apply_pending,
    _add_pictures_apply_ready,
    render_edit_page,
    render_final_preview_step,
)
from app_modules.workflow_config import FLOW_STAGES, STAGE_COPY, STAGE_LABELS
from app_modules.workflow_state import session_stage_from_state
from layout_policy import DEFAULT_DAY_PAGE_LAYOUT


def _session_stage() -> str:
    return session_stage_from_state(st.session_state)


def render_app(app_version: str) -> None:
    st.session_state.setdefault("day_page_layout", DEFAULT_DAY_PAGE_LAYOUT)
    stage = _session_stage()
    if stage == "input":
        render_input_page(app_version)
    elif stage == "edit":
        render_edit_page(app_version)
    elif stage == "pictures":
        render_picture_page(app_version)
    elif stage == "export":
        render_export_page(app_version)
    else:
        render_input_page(app_version)

    render_debug_tools()

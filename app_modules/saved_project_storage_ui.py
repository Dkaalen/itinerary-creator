"""Render compact saved-project storage guidance."""

from __future__ import annotations

import streamlit as st

from app_modules.saved_project_storage_decision import get_saved_project_storage_decision


def render_saved_project_storage_note() -> None:
    """Render the current saved-project storage mode without backlog controls."""

    decision = get_saved_project_storage_decision()
    st.caption(decision.user_summary)

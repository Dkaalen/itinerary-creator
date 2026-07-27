"""Shared Streamlit styling for the internal itinerary app."""

from __future__ import annotations

import streamlit as st

from ui import (
    style_app_shell,
    style_component_layout,
    style_debug,
    style_export,
    style_forms,
    style_image_bank,
    style_responsive,
    style_tokens,
    style_workflow,
)

STYLE_SECTIONS = (
    style_tokens.CSS,
    style_app_shell.CSS,
    style_forms.CSS,
    style_component_layout.CSS,
    style_workflow.CSS,
    style_export.CSS,
    style_image_bank.CSS,
    style_debug.CSS,
    style_responsive.CSS,
)


def build_global_css() -> str:
    """Return the app-wide CSS assembled by responsibility."""

    return "\n\n".join(section.strip() for section in STYLE_SECTIONS if section.strip())


def apply_global_styles():
    st.markdown(
        f"""
        <style>
        {build_global_css()}
        </style>
        """,
        unsafe_allow_html=True,
    )

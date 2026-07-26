"""Supported Streamlit application bootstrap.

Importing this module is intentionally side-effect free. Streamlit and every
application surface are imported only when :func:`run_streamlit_app` executes
from the single supported root entry point, ``app.py``.
"""

from __future__ import annotations


def run_streamlit_app() -> None:
    """Configure Streamlit, initialize lightweight defaults, and route once."""

    import streamlit as st

    st.set_page_config(
        page_title="Itinerary Creator",
        page_icon="🧭",
        layout="wide",
    )

    from app_modules.app_version import APP_VERSION
    from app_modules.main_view import render_app
    from app_modules.workflow_state import ensure_workflow_defaults
    from ui.styles import apply_global_styles

    apply_global_styles()
    ensure_workflow_defaults(st.session_state)
    render_app(APP_VERSION, state=st.session_state)


__all__ = ["run_streamlit_app"]

"""Supported Streamlit application bootstrap.

Importing this module is intentionally side-effect free. Streamlit and every
application surface are imported only when :func:`run_streamlit_app` executes
from the single supported root entry point, ``app.py``.
"""

from __future__ import annotations

from time import perf_counter


def run_streamlit_app() -> None:
    """Configure Streamlit, initialize lightweight defaults, and route once."""

    import streamlit as st

    st.set_page_config(
        page_title="Itinerary Creator",
        page_icon="🧭",
        layout="wide",
    )

    from app_modules.app_version import APP_VERSION
    from app_modules.browser_storage_guard import render_browser_storage_guard
    from app_modules.main_view import render_app
    from app_modules.performance_telemetry import begin_rerun, record_timing, record_trace
    from app_modules.workflow_state import ensure_workflow_defaults
    from ui.styles import apply_global_styles

    started = perf_counter()
    rerun_number = begin_rerun(st.session_state)
    try:
        apply_global_styles()
        render_browser_storage_guard(st.session_state)
        ensure_workflow_defaults(st.session_state)
        render_app(APP_VERSION, state=st.session_state)
    except Exception as exc:
        record_trace(
            st.session_state,
            "streamlit_rerun_failed",
            rerun=rerun_number,
            error_type=type(exc).__name__,
        )
        raise
    finally:
        record_timing(
            st.session_state,
            "streamlit_rerun",
            perf_counter() - started,
            note=f"rerun:{rerun_number}",
        )


__all__ = ["run_streamlit_app"]

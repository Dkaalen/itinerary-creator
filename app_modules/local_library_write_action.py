"""Apply Local Library write results to Streamlit state and feedback."""

from __future__ import annotations

import streamlit as st

from app_modules.calculator_library_cache import clear_cached_local_library
from app_modules.local_library_state import SELECTED_LIBRARY_ROW_KEY


def handle_local_library_write_result(result: object, selected_id: str, *, success_message: str | None = None) -> None:
    """Show feedback for a Local Library write and refresh cached rows."""

    if getattr(result, "ok", False):
        clear_cached_local_library(st.session_state)
        st.session_state[SELECTED_LIBRARY_ROW_KEY] = selected_id
        st.success(success_message or getattr(result, "message", "Saved Local Library row."))
        st.rerun()
    else:
        st.error(getattr(result, "message", "Could not save Local Library row."))

"""Render Local Library refresh and status controls for the calculator page."""

from __future__ import annotations

import streamlit as st

from calculator.library_read_summary import summarize_local_library_read
from calculator.library_store import LocalLibraryReadResult

_REFRESH_BUTTON_KEY = "calculator_refresh_local_library"


def render_local_library_refresh_control() -> bool:
    """Render the calculator Local Library refresh button."""

    left, right = st.columns([1, 3])
    with left:
        refresh_requested = st.button(
            "Refresh Local Library",
            key=_REFRESH_BUTTON_KEY,
            help="Reload calculator autocomplete rows from Google Sheets instead of using the cached result.",
            use_container_width=True,
        )
    with right:
        st.caption("Travel element autocomplete uses the Local Library. Refresh after changing the Google Sheet.")
    return bool(refresh_requested)


def render_local_library_status(read_result: LocalLibraryReadResult, *, refreshed: bool = False) -> None:
    """Show whether Local Library autocomplete is live or using fallback data."""

    summary = summarize_local_library_read(read_result)
    prefix = "Refreshed. " if refreshed else ""
    if summary.level == "success":
        st.caption(prefix + summary.headline)
        return
    st.warning(prefix + summary.headline + "\n\n" + summary.detail)

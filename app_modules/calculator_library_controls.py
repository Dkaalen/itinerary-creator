"""Render Local Library refresh and status controls for the calculator page."""

from __future__ import annotations

import streamlit as st

from calculator.library_read_summary import summarize_local_library_read
from calculator.library_store import LocalLibraryReadResult

_REFRESH_BUTTON_KEY = "calculator_refresh_local_library"


def render_local_library_refresh_control() -> bool:
    """Render the calculator Local Library refresh button."""

    left, right = st.columns([0.22, 0.78])
    with left:
        refresh_requested = st.button(
            "Refresh library",
            key=_REFRESH_BUTTON_KEY,
            help="Reload autocomplete rows from the active Local Library source.",
            use_container_width=True,
        )
    with right:
        st.caption("Autocomplete reads from the Local Library. Refresh after editing the shared sheet.")
    return bool(refresh_requested)


def render_local_library_status(read_result: LocalLibraryReadResult, *, refreshed: bool = False) -> None:
    """Show the active Local Library source without interrupting the workflow."""

    summary = summarize_local_library_read(read_result)
    prefix = "Refreshed · " if refreshed else ""
    if summary.level == "success":
        st.caption(prefix + summary.headline)
        return
    st.caption(prefix + summary.headline)

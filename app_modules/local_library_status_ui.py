"""Render Local Library source and read-only status messages."""

from __future__ import annotations

import streamlit as st

from calculator.library_read_summary import summarize_local_library_read
from calculator.library_store import LocalLibraryReadResult


def render_local_library_source_status(library_read: LocalLibraryReadResult) -> None:
    """Render the active Local Library source status."""

    summary = summarize_local_library_read(library_read)
    if summary.level == "success":
        st.success(summary.headline)
        st.caption(summary.detail)
        return

    st.error(summary.headline)
    st.caption(summary.detail)

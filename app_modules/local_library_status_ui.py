"""Render advanced Local Library workbook diagnostics."""

from __future__ import annotations

import streamlit as st

from calculator.library_read_summary import summarize_local_library_read
from calculator.library_store import LocalLibraryReadResult


def render_local_library_source_status(
    library_read: LocalLibraryReadResult,
    *,
    refreshed: bool = False,
) -> None:
    """Render technical source status and actionable workbook diagnostics."""

    summary = summarize_local_library_read(library_read)
    prefix = "Refreshed · " if refreshed else ""
    if summary.level == "success":
        st.success(f"{prefix}{summary.headline}")
    elif summary.level == "warning":
        st.warning(f"{prefix}{summary.headline}")
    else:
        st.error(f"{prefix}{summary.headline}")
    st.caption(summary.detail)

    metrics = st.columns(4)
    metrics[0].metric("Valid records", summary.total_rows)
    metrics[1].metric("Fetchable records", summary.fetchable_rows)
    metrics[2].metric("Diagnostics", len(library_read.diagnostics))
    metrics[3].metric("Load time", f"{library_read.load_time_seconds:.3f} s")
    st.caption(f"Workbook fingerprint: `{library_read.fingerprint or 'Unavailable'}`")
    _render_diagnostics(library_read)


def _render_diagnostics(library_read: LocalLibraryReadResult) -> None:
    diagnostics = tuple(library_read.diagnostics)
    if not diagnostics:
        st.caption("No workbook warnings or invalid records were reported.")
        return
    visible_limit = 50
    st.markdown(f"**Workbook diagnostics ({len(diagnostics)})**")
    for issue in diagnostics[:visible_limit]:
        st.write(f"• {issue.message}")
    hidden_count = len(diagnostics) - visible_limit
    if hidden_count > 0:
        st.caption(f"{hidden_count} additional diagnostics are not shown here.")

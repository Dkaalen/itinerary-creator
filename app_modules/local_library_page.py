"""Render the read-only Local Library browser page."""

from __future__ import annotations

import streamlit as st

from app_modules.app_header import _render_app_header
from app_modules.calculator_library_cache import read_cached_local_library
from app_modules.calculator_navigation import open_calculator_page
from app_modules.input_workspace import render_studio_brand
from app_modules.local_library_browser_ui import render_local_library_browser
from app_modules.local_library_status_ui import render_local_library_source_status


def render_local_library_page(app_version: str) -> None:
    """Render the bundled workbook as a searchable, read-only record browser."""

    _render_app_header(app_version, stage="input")
    _render_local_library_topbar()
    _render_local_library_header()

    st.info(
        "Local Library records are maintained in the bundled Excel workbook. "
        "Edit the workbook and redeploy the app to change these records."
    )
    advanced = st.expander("Advanced diagnostics")
    refresh_requested = advanced.button(
        "Refresh Local Library",
        use_container_width=True,
        key="local_library_browser_refresh",
    )
    library_read = read_cached_local_library(st.session_state, force_refresh=refresh_requested)
    with advanced:
        render_local_library_source_status(library_read, refreshed=refresh_requested)

    render_local_library_browser(library_read)


def _render_local_library_topbar() -> None:
    brand_col, back_col = st.columns([0.76, 0.24], vertical_alignment="center")
    with brand_col:
        render_studio_brand()
    with back_col:
        if st.button("Back to itinerary calculator", use_container_width=True):
            open_calculator_page(st.session_state)
            st.rerun()


def _render_local_library_header() -> None:
    st.html(
        """
        <section class="workspace-page-heading local-library-heading">
          <span class="local-library-kicker">Reusable rows</span>
          <h1>Local Library</h1>
          <p>Browse the bundled Excel workbook used by Calculator autocomplete.</p>
        </section>
        """
    )

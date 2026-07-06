"""Render the Local Library management page shell."""

from __future__ import annotations

import streamlit as st

from app_modules.app_header import _render_app_header
from app_modules.calculator_library_cache import read_cached_local_library
from app_modules.calculator_navigation import open_calculator_page
from app_modules.local_library_editor_form import render_local_library_editor
from app_modules.local_library_selector_ui import render_local_library_row_selector
from app_modules.local_library_status_ui import render_local_library_source_status


def render_local_library_page(app_version: str) -> None:
    """Render Local Library browse/add/edit/remove controls."""

    _render_app_header(app_version, stage="input")
    _render_local_library_topbar()
    _render_local_library_header()

    library_read = read_cached_local_library(st.session_state, force_refresh=st.button("Refresh Local Library"))
    render_local_library_source_status(library_read)

    selected_row = render_local_library_row_selector(library_read)
    render_local_library_editor(selected_row, library_read)


def _render_local_library_topbar() -> None:
    brand_col, back_col = st.columns([0.76, 0.24], vertical_alignment="center")
    with brand_col:
        st.html('<div class="studio-toolbar"><span class="studio-wordmark">Itinerary Studio</span></div>')
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
        </section>
        """
    )

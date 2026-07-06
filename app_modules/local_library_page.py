"""Render the Local Library management page shell."""

from __future__ import annotations

import streamlit as st

from app_modules.app_header import _render_app_header, _stage_panel
from app_modules.calculator_library_cache import read_cached_local_library
from app_modules.calculator_navigation import open_calculator_page
from app_modules.local_library_editor_form import render_local_library_editor
from app_modules.local_library_selector_ui import render_local_library_row_selector
from app_modules.local_library_status_ui import render_local_library_source_status


def render_local_library_page(app_version: str) -> None:
    """Render Local Library browse/add/edit/remove controls."""

    _render_app_header(app_version, stage="input")
    _stage_panel(
        "Local Library",
        "Add, edit, or remove reusable calculator rows. Google Sheets powers shared editing; the bundled library keeps autocomplete available offline.",
    )
    _render_local_library_hero()
    _render_top_actions()

    library_read = read_cached_local_library(st.session_state, force_refresh=st.button("Refresh Local Library"))
    render_local_library_source_status(library_read)

    selected_row = render_local_library_row_selector(library_read)
    render_local_library_editor(selected_row, library_read)


def _render_local_library_hero() -> None:
    st.html(
        """
        <section class="local-library-hero">
          <span class="local-library-kicker">Reusable rows</span>
          <h1 class="local-library-title">Local Library</h1>
          <p class="local-library-description">Manage reusable calculator rows for autocomplete.</p>
        </section>
        """
    )


def _render_top_actions() -> None:
    action_col, help_col = st.columns([0.22, 0.78], vertical_alignment="center")
    with action_col:
        if st.button("Back to calculator", use_container_width=True):
            open_calculator_page(st.session_state)
            st.rerun()
    with help_col:
        st.empty()

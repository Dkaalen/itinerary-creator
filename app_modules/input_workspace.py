"""Focused HTML helpers for the itinerary input workspace."""

from __future__ import annotations

import streamlit as st


def render_input_toolbar() -> None:
    """Render the quiet workspace wordmark used by the top action row."""

    st.html('<div class="studio-toolbar"><span class="studio-wordmark">Itinerary Studio</span></div>')


def render_input_header() -> None:
    """Render the simple input page heading."""

    st.html(
        """
        <header class="input-page-heading">
          <h1>New itinerary</h1>
        </header>
        """
    )


def render_source_label() -> None:
    """Render the quiet label above the raw itinerary input."""

    st.html('<div class="source-line"><span>Supplier rows</span></div>')

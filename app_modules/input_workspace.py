"""Focused HTML helpers for the itinerary input workspace."""

from __future__ import annotations

import streamlit as st


def render_input_toolbar() -> None:
    """Render a compact workspace identity strip without landing-page bloat."""

    st.html(
        """
        <div class="studio-toolbar">
          <div>
            <span class="studio-wordmark">Itinerary Studio</span>
            <span class="studio-toolbar-note">Create, edit, picture, export.</span>
          </div>
        </div>
        """
    )


def render_input_header() -> None:
    """Render the simple input page heading."""

    st.html(
        """
        <header class="input-page-heading">
          <h1>New itinerary</h1>
          <p>Paste supplier rows or start from the calculator. The generated itinerary opens in the editor.</p>
        </header>
        """
    )


def render_source_label() -> None:
    """Render the quiet label above the raw itinerary input."""

    st.html(
        """
        <div class="source-line">
          <span>Supplier rows</span>
          <small>Messy Excel or supplier text is fine.</small>
        </div>
        """
    )


def render_generation_action_bar() -> None:
    """Render a minimal anchor above the generation actions."""

    st.html(
        """
        <div class="generate-line">
          <span>Generate itinerary</span>
        </div>
        """
    )

"""Focused HTML helpers for the itinerary workspace."""

from __future__ import annotations

import base64
from functools import lru_cache
from html import escape

import streamlit as st

from app_modules.output_brand import BOOKNORDICS_SYMBOL_PATH

BOOKNORDICS_HOME_URL = "https://booknordics.com/"


@lru_cache(maxsize=1)
def _booknordics_logo_data_uri() -> str:
    """Return the embedded Booknordics symbol for the app workspace header."""

    if not BOOKNORDICS_SYMBOL_PATH.is_file():
        return ""
    encoded = base64.b64encode(BOOKNORDICS_SYMBOL_PATH.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render_studio_brand() -> None:
    """Render the linked Booknordics workspace brand block."""

    logo_src = _booknordics_logo_data_uri()
    logo_html = f'<img src="{escape(logo_src)}" alt="Booknordics.com symbol" />' if logo_src else ""
    st.html(
        f"""
        <a class="studio-brand-link" href="{BOOKNORDICS_HOME_URL}" target="_blank" rel="noopener noreferrer">
          <span class="studio-brand-logo">{logo_html}</span>
          <span class="studio-brand-copy">
            <strong>Itinerary Studio</strong>
            <span>By Booknordics.com</span>
          </span>
        </a>
        """
    )


def render_input_toolbar() -> None:
    """Backward-compatible input helper for the workspace brand block."""

    render_studio_brand()


def render_input_header() -> None:
    """Render the input page heading."""

    st.html(
        """
        <header class="input-page-heading">
          <span class="input-page-kicker">Create</span>
          <h1>New itinerary</h1>
          <p>Start with a name and paste your supplier rows to generate your itineraries.</p>
        </header>
        """
    )


def render_source_label() -> None:
    """Render the quiet label above the raw itinerary input."""

    st.html('<div class="source-line"><span>Supplier rows</span></div>')

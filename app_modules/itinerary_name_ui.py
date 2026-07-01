"""Render the optional itinerary-name input."""

from __future__ import annotations

import streamlit as st

from app_modules.itinerary_name_state import ITINERARY_NAME_INPUT_KEY, seed_itinerary_name_input


def render_itinerary_name_input() -> None:
    """Render the optional itinerary-name field above the supplier text box."""

    seed_itinerary_name_input(st.session_state)
    st.text_input(
        "Itinerary Name",
        key=ITINERARY_NAME_INPUT_KEY,
        placeholder="Norway Winter Group - Jan 2027",
        help="Optional. Use this to save a named project; unnamed generation still works.",
    )

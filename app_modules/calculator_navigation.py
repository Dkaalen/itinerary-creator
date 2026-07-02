"""Navigation helpers for the in-app calculator page."""

from __future__ import annotations

from typing import Any, MutableMapping

import streamlit as st

from calculator.calculator_state import add_row, create_calculator_state

APP_PAGE_KEY = "active_app_page"
WORKFLOW_PAGE = "workflow"
CALCULATOR_PAGE = "calculator"
CALCULATOR_STATE_KEY = "calculator_state"


def calculator_page_is_active(state: MutableMapping[str, Any]) -> bool:
    """Return whether the calculator page route is active."""

    return state.get(APP_PAGE_KEY, WORKFLOW_PAGE) == CALCULATOR_PAGE


def open_calculator_page(state: MutableMapping[str, Any]) -> None:
    """Route the app to the calculator and create a first row if needed."""

    state[APP_PAGE_KEY] = CALCULATOR_PAGE
    if state.get(CALCULATOR_STATE_KEY) is None:
        itinerary_name = str(state.get("itinerary_name") or state.get("itinerary_name_input") or "")
        state[CALCULATOR_STATE_KEY] = add_row(create_calculator_state(itinerary_name))


def close_calculator_page(state: MutableMapping[str, Any]) -> None:
    """Route the app back to the normal itinerary workflow."""

    state[APP_PAGE_KEY] = WORKFLOW_PAGE


def render_calculator_entry_button() -> None:
    """Render the front-page calculator entry action."""

    if st.button("Calculate itinerary", type="primary", use_container_width=True):
        open_calculator_page(st.session_state)
        st.rerun()

"""Navigation helpers for the in-app calculator page."""

from __future__ import annotations

from typing import Any, MutableMapping

import streamlit as st

from calculator.calculator_state import create_initial_calculator_state

APP_PAGE_KEY = "active_app_page"
WORKFLOW_PAGE = "workflow"
CALCULATOR_PAGE = "calculator"
LOCAL_LIBRARY_PAGE = "local_library"
CALCULATOR_STATE_KEY = "calculator_state"


def calculator_page_is_active(state: MutableMapping[str, Any]) -> bool:
    """Return whether the calculator page route is active."""

    return state.get(APP_PAGE_KEY, WORKFLOW_PAGE) == CALCULATOR_PAGE


def open_calculator_page(state: MutableMapping[str, Any]) -> None:
    """Route the app to the calculator and create startup rows if needed."""

    state[APP_PAGE_KEY] = CALCULATOR_PAGE
    calculator_state = state.get(CALCULATOR_STATE_KEY)
    if calculator_state is None or not getattr(calculator_state, "rows", ()):
        itinerary_name = str(state.get("itinerary_name") or state.get("itinerary_name_input") or "")
        state[CALCULATOR_STATE_KEY] = create_initial_calculator_state(itinerary_name)


def local_library_page_is_active(state: MutableMapping[str, Any]) -> bool:
    """Return whether the Local Library management page route is active."""

    return state.get(APP_PAGE_KEY, WORKFLOW_PAGE) == LOCAL_LIBRARY_PAGE


def open_local_library_page(state: MutableMapping[str, Any]) -> None:
    """Route the app to Local Library management."""

    state[APP_PAGE_KEY] = LOCAL_LIBRARY_PAGE


def close_calculator_page(state: MutableMapping[str, Any]) -> None:
    """Route the app back to the normal itinerary workflow."""

    state[APP_PAGE_KEY] = WORKFLOW_PAGE


def render_calculator_entry_button() -> None:
    """Render a compact calculator entry action."""

    action_col, help_col = st.columns([0.22, 0.78], vertical_alignment="center")
    with action_col:
        open_requested = st.button("Open calculator", type="primary", use_container_width=True)
    with help_col:
        st.caption("Build, price, export, and generate an itinerary from the in-app spreadsheet.")
    if open_requested:
        open_calculator_page(st.session_state)
        st.rerun()

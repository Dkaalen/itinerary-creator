"""Navigation helpers for the in-app calculator page."""

from __future__ import annotations

from typing import Any, MutableMapping
from uuid import uuid4

try:
    import streamlit as st
except ModuleNotFoundError:  # Keep navigation helpers testable without Streamlit.
    st = None

from app_modules.calculator_state_keys import (
    CALCULATOR_DRAFT_NAMESPACE_KEY,
    CALCULATOR_RETURN_AVAILABLE_KEY,
    CALCULATOR_STATE_KEY,
)

from app_modules.session_state_keys import (
    ACTIVE_APP_PAGE_KEY as APP_PAGE_KEY,
    CALCULATOR_PAGE,
    LOCAL_LIBRARY_PAGE,
    WORKFLOW_PAGE,
)
from app_modules.workflow_navigation import (
    route_to_calculator,
    route_to_local_library,
    route_to_workflow,
)


def _streamlit_api():
    global st
    if st is None:
        import streamlit as streamlit_api

        st = streamlit_api
    return st


def calculator_page_is_active(state: MutableMapping[str, Any]) -> bool:
    """Return whether the calculator page route is active."""

    return state.get(APP_PAGE_KEY, WORKFLOW_PAGE) == CALCULATOR_PAGE


def calculator_draft_namespace(state: MutableMapping[str, Any]) -> str:
    """Return a stable browser-draft namespace for the current calculator workspace.

    Unsaved itineraries need a namespace that survives itinerary-name edits in
    the same browser session. Saved projects use their durable project id so a
    reopened project can recover the matching local browser draft without
    leaking rows into another itinerary.
    """

    from app_modules.project_identity import active_project_id_from_state

    project_id = active_project_id_from_state(state)
    if project_id:
        namespace = f"project:{project_id}"
        state[CALCULATOR_DRAFT_NAMESPACE_KEY] = namespace
        return namespace

    existing = str(state.get(CALCULATOR_DRAFT_NAMESPACE_KEY) or "").strip()
    if existing:
        return existing

    namespace = f"session:{uuid4().hex}"
    state[CALCULATOR_DRAFT_NAMESPACE_KEY] = namespace
    return namespace


def open_calculator_page(state: MutableMapping[str, Any]) -> None:
    """Route the app to the calculator and create startup rows if needed."""

    from app_modules.calculator_session_state import calculator_state_from_session

    route_to_calculator(state)
    calculator_draft_namespace(state)
    calculator_state_from_session(state)


def local_library_page_is_active(state: MutableMapping[str, Any]) -> bool:
    """Return whether the Local Library management page route is active."""

    return state.get(APP_PAGE_KEY, WORKFLOW_PAGE) == LOCAL_LIBRARY_PAGE


def return_to_calculator_page(state: MutableMapping[str, Any]) -> None:
    """Return to an existing Calculator workspace without creating a new route contract."""

    from app_modules.calculator_session_state import calculator_state_from_session

    route_to_calculator(state)
    calculator_draft_namespace(state)
    calculator_state_from_session(state)


def open_local_library_page(state: MutableMapping[str, Any]) -> None:
    """Route the app to Local Library management."""

    route_to_local_library(state)


def close_calculator_page(state: MutableMapping[str, Any]) -> None:
    """Route the app back to the normal itinerary workflow."""

    route_to_workflow(state)


def render_back_to_main_page_button() -> None:
    """Render a page-level escape route from Calculator to the main workspace.

    The Calculator grid also emits a synchronized ``close`` action, but this
    Streamlit-owned control remains visible even when the embedded grid has not
    mounted, is scrolled, or is using full-screen browser layout. Routing back
    does not clear Calculator state or its browser-draft namespace.
    """

    ui = _streamlit_api()
    if ui.button(
        "Back to main page",
        use_container_width=False,
        help="Return to the main itinerary workspace without clearing the Calculator.",
        key="calculator_back_to_main_page",
    ):
        close_calculator_page(ui.session_state)
        ui.rerun()


def calculator_return_is_available(state: MutableMapping[str, Any]) -> bool:
    """Return whether the current itinerary was generated from Calculator state."""

    return bool(state.get(CALCULATOR_RETURN_AVAILABLE_KEY) and state.get(CALCULATOR_STATE_KEY))


def render_return_to_calculator_button() -> None:
    """Render a safe route back to the preserved Calculator workspace."""

    ui = _streamlit_api()
    if not calculator_return_is_available(ui.session_state):
        return
    if ui.button(
        "Back to Calculator",
        use_container_width=True,
        help="Return to the same calculation rows without regenerating the itinerary.",
        key="return_to_calculator_from_itinerary",
    ):
        return_to_calculator_page(ui.session_state)
        ui.rerun()


def render_calculator_entry_button() -> None:
    """Render a calm calculator entry action for the input workspace."""

    ui = _streamlit_api()
    open_requested = ui.button(
        "Open calculator",
        use_container_width=True,
        help="Build, price, export, and generate an itinerary from the in-app spreadsheet.",
    )
    ui.caption("Pricing, Local Library autocomplete, Excel export, then itinerary generation.")
    if open_requested:
        open_calculator_page(ui.session_state)
        ui.rerun()

"""Session-state authority for the calculator workflow."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from app_modules.calculator_component_result import CalculatorGridResult
from app_modules.calculator_state_keys import (
    CALCULATOR_ADVANCED_TOGGLE_KEY,
    CALCULATOR_BACKUP_UPLOAD_KEY,
    CALCULATOR_DRAFT_NAMESPACE_KEY,
    CALCULATOR_ITINERARY_NAME_INPUT_KEY,
    CALCULATOR_ITINERARY_NAME_SYNC_REQUIRED_KEY,
    CALCULATOR_READY_DOWNLOAD_KEY,
    CALCULATOR_RETURN_AVAILABLE_KEY,
    CALCULATOR_COMPONENT_ACK_KEY,
    CALCULATOR_PROCESSED_REQUEST_IDS_KEY,
    CALCULATOR_GENERATION_FEEDBACK_KEY,
    CALCULATOR_STATE_KEY,
    LEGACY_CALCULATOR_SESSION_KEYS,
    LEGACY_CALCULATOR_SESSION_PREFIXES,
)
from calculator.calculator_state import CalculatorState, create_initial_calculator_state


def calculator_state_from_session(state: MutableMapping[str, Any]) -> CalculatorState:
    """Return the active calculator state, creating startup rows when needed."""

    existing = state.get(CALCULATOR_STATE_KEY)
    if isinstance(existing, CalculatorState) and existing.rows:
        return existing
    itinerary_name = str(
        getattr(existing, "itinerary_name", "")
        or state.get("itinerary_name")
        or state.get("itinerary_name_input")
        or ""
    )
    new_state = create_initial_calculator_state(itinerary_name)
    store_calculator_state(state, new_state)
    return new_state


def store_calculator_state(
    state: MutableMapping[str, Any],
    calculator_state: CalculatorState,
    *,
    clear_ready_download: bool = True,
    sync_name_input: bool = False,
) -> None:
    """Persist calculator state and invalidate stale staged Excel downloads.

    Do not write to the Streamlit text-input key here. Streamlit forbids
    assigning to a widget-owned key after the widget has been instantiated in
    the current run. The page renderer syncs that widget key before rendering
    the widget instead.
    """

    previous = state.get(CALCULATOR_STATE_KEY)
    state[CALCULATOR_STATE_KEY] = calculator_state
    if sync_name_input:
        state[CALCULATOR_ITINERARY_NAME_SYNC_REQUIRED_KEY] = True
    if clear_ready_download and previous != calculator_state:
        clear_ready_calculation_download(state)


def sync_calculator_itinerary_name_input(state: MutableMapping[str, Any]) -> None:
    """Sync the itinerary-name widget key before the text input is rendered."""

    calculator_state = calculator_state_from_session(state)
    sync_required = bool(state.pop(CALCULATOR_ITINERARY_NAME_SYNC_REQUIRED_KEY, False))
    if sync_required or CALCULATOR_ITINERARY_NAME_INPUT_KEY not in state:
        state[CALCULATOR_ITINERARY_NAME_INPUT_KEY] = calculator_state.itinerary_name


def update_calculator_itinerary_name(state: MutableMapping[str, Any], itinerary_name: str) -> CalculatorState:
    """Persist a calculator itinerary-name edit through the same state authority."""

    calculator_state = calculator_state_from_session(state).with_itinerary_name(itinerary_name)
    store_calculator_state(state, calculator_state)
    return calculator_state


def apply_calculator_grid_result(state: MutableMapping[str, Any], result: CalculatorGridResult) -> CalculatorState:
    """Apply browser-grid state and UI toggles returned from the component."""

    state[CALCULATOR_ADVANCED_TOGGLE_KEY] = result.show_advanced
    store_calculator_state(state, result.state)
    return result.state


def clear_ready_calculation_download(state: MutableMapping[str, Any]) -> None:
    """Remove staged calculator Excel bytes from session state."""

    state.pop(CALCULATOR_READY_DOWNLOAD_KEY, None)


def clear_calculator_project_state(state: MutableMapping[str, Any]) -> None:
    """Clear calculator state that must not survive a hard project reset."""

    keys = (
        CALCULATOR_STATE_KEY,
        CALCULATOR_ADVANCED_TOGGLE_KEY,
        CALCULATOR_ITINERARY_NAME_INPUT_KEY,
        CALCULATOR_ITINERARY_NAME_SYNC_REQUIRED_KEY,
        CALCULATOR_BACKUP_UPLOAD_KEY,
        CALCULATOR_DRAFT_NAMESPACE_KEY,
        CALCULATOR_READY_DOWNLOAD_KEY,
        CALCULATOR_RETURN_AVAILABLE_KEY,
        CALCULATOR_COMPONENT_ACK_KEY,
        CALCULATOR_PROCESSED_REQUEST_IDS_KEY,
        CALCULATOR_GENERATION_FEEDBACK_KEY,
        *LEGACY_CALCULATOR_SESSION_KEYS,
    )
    for key in keys:
        state.pop(key, None)
    for key in tuple(state.keys()):
        if any(str(key).startswith(prefix) for prefix in LEGACY_CALCULATOR_SESSION_PREFIXES):
            state.pop(key, None)

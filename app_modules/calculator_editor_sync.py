"""Synchronize calculator state changes with the Streamlit grid editor."""

from __future__ import annotations

from typing import Any, MutableMapping

from app_modules.calculator_navigation import CALCULATOR_STATE_KEY
from calculator.calculator_state import CalculatorState

CALCULATOR_GRID_REVISION_KEY = "calculator_grid_revision"
CALCULATOR_GRID_WIDGET_PREFIX = "calculator_grid_editor"


def calculator_grid_widget_key(state: MutableMapping[str, Any]) -> str:
    """Return the current grid widget key for Streamlit data editor."""

    return f"{CALCULATOR_GRID_WIDGET_PREFIX}_{_current_revision(state)}"


def store_calculator_state(
    session_state: MutableMapping[str, Any],
    calculator_state: CalculatorState,
    *,
    refresh_grid: bool = False,
) -> None:
    """Persist calculator state and optionally force the grid widget to remount."""

    session_state[CALCULATOR_STATE_KEY] = calculator_state
    if refresh_grid:
        bump_calculator_grid_revision(session_state)


def bump_calculator_grid_revision(state: MutableMapping[str, Any]) -> int:
    """Increment and return the calculator grid revision."""

    previous_revision = _current_revision(state)
    state.pop(f"{CALCULATOR_GRID_WIDGET_PREFIX}_{previous_revision}", None)
    revision = previous_revision + 1
    state.pop(f"{CALCULATOR_GRID_WIDGET_PREFIX}_{revision}", None)
    state[CALCULATOR_GRID_REVISION_KEY] = revision
    return revision


def _current_revision(state: MutableMapping[str, Any]) -> int:
    try:
        return int(state.get(CALCULATOR_GRID_REVISION_KEY, 0) or 0)
    except (TypeError, ValueError):
        return 0

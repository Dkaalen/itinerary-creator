from __future__ import annotations

from app_modules.calculator_editor_sync import (
    CALCULATOR_GRID_REVISION_KEY,
    calculator_grid_widget_key,
    store_calculator_state,
)
from app_modules.calculator_navigation import CALCULATOR_STATE_KEY
from calculator.calculator_state import CalculatorState


def test_store_calculator_state_can_force_grid_widget_refresh() -> None:
    session_state: dict[str, object] = {"calculator_grid_editor_0": [{"row_id": "1"}]}
    state = CalculatorState(itinerary_name="Trip")

    store_calculator_state(session_state, state)
    first_key = calculator_grid_widget_key(session_state)

    store_calculator_state(session_state, state, refresh_grid=True)

    assert session_state[CALCULATOR_STATE_KEY] == state
    assert session_state[CALCULATOR_GRID_REVISION_KEY] == 1
    assert calculator_grid_widget_key(session_state) != first_key
    assert "calculator_grid_editor_0" not in session_state

from __future__ import annotations

from app_modules.calculator_session_state import (
    apply_calculator_grid_result,
    calculator_state_from_session,
    clear_calculator_project_state,
    store_calculator_state,
    update_calculator_itinerary_name,
)
from app_modules.calculator_component_result import CalculatorGridResult
from app_modules.calculator_state_keys import (
    CALCULATOR_ADVANCED_TOGGLE_KEY,
    CALCULATOR_DRAFT_NAMESPACE_KEY,
    CALCULATOR_ITINERARY_NAME_INPUT_KEY,
    CALCULATOR_READY_DOWNLOAD_KEY,
    CALCULATOR_STATE_KEY,
)
from calculator.calculator_state import CalculatorState
from calculator.row_model import CalculatorRow


def test_calculator_state_from_session_rehydrates_blank_saved_snapshot() -> None:
    session_state: dict[str, object] = {
        "itinerary_name": "Saved Trip",
        CALCULATOR_STATE_KEY: CalculatorState(itinerary_name="Saved Trip", rows=()),
    }

    state = calculator_state_from_session(session_state)

    assert state.itinerary_name == "Saved Trip"
    assert len(state.rows) == 25
    assert session_state[CALCULATOR_STATE_KEY] == state


def test_store_calculator_state_clears_stale_prepared_excel_after_real_change() -> None:
    session_state: dict[str, object] = {
        CALCULATOR_STATE_KEY: CalculatorState(itinerary_name="Trip", rows=(CalculatorRow(row_id="1"),)),
        CALCULATOR_READY_DOWNLOAD_KEY: {"filename": "old.xlsx", "content": b"old"},
    }
    changed = CalculatorState(itinerary_name="Trip", rows=(CalculatorRow(row_id="1", travel_element="Hotel"),))

    store_calculator_state(session_state, changed)

    assert session_state[CALCULATOR_STATE_KEY] == changed
    assert CALCULATOR_READY_DOWNLOAD_KEY not in session_state


def test_store_calculator_state_keeps_ready_excel_when_state_is_unchanged() -> None:
    state = CalculatorState(itinerary_name="Trip", rows=(CalculatorRow(row_id="1", travel_element="Hotel"),))
    session_state: dict[str, object] = {
        CALCULATOR_STATE_KEY: state,
        CALCULATOR_READY_DOWNLOAD_KEY: {"filename": "current.xlsx", "content": b"xlsx"},
    }

    store_calculator_state(session_state, state)

    assert CALCULATOR_READY_DOWNLOAD_KEY in session_state


def test_update_calculator_itinerary_name_uses_same_state_authority() -> None:
    session_state: dict[str, object] = {
        CALCULATOR_STATE_KEY: CalculatorState(itinerary_name="Old", rows=(CalculatorRow(row_id="1"),)),
        CALCULATOR_READY_DOWNLOAD_KEY: {"filename": "old.xlsx", "content": b"old"},
    }

    state = update_calculator_itinerary_name(session_state, "New")

    assert state.itinerary_name == "New"
    assert session_state[CALCULATOR_ITINERARY_NAME_INPUT_KEY] == "New"
    assert CALCULATOR_READY_DOWNLOAD_KEY not in session_state


def test_apply_calculator_grid_result_persists_rows_and_advanced_toggle() -> None:
    grid_state = CalculatorState(itinerary_name="Trip", rows=(CalculatorRow(row_id="1", travel_element="Museum"),))
    result = CalculatorGridResult(action="sync", state=grid_state, show_advanced=True)
    session_state: dict[str, object] = {CALCULATOR_READY_DOWNLOAD_KEY: {"filename": "old.xlsx", "content": b"old"}}

    applied = apply_calculator_grid_result(session_state, result)

    assert applied == grid_state
    assert session_state[CALCULATOR_STATE_KEY] == grid_state
    assert session_state[CALCULATOR_ADVANCED_TOGGLE_KEY] is True
    assert CALCULATOR_READY_DOWNLOAD_KEY not in session_state


def test_clear_calculator_project_state_removes_current_and_retired_keys() -> None:
    session_state: dict[str, object] = {
        CALCULATOR_STATE_KEY: object(),
        CALCULATOR_ADVANCED_TOGGLE_KEY: True,
        CALCULATOR_DRAFT_NAMESPACE_KEY: "session:abc",
        CALCULATOR_READY_DOWNLOAD_KEY: {"content": b"xlsx"},
        "calculator_grid_revision": 7,
        "calculator_grid_editor_7": [{"row_id": "old"}],
        "calculator_travel_element_autocomplete_query": "hotel",
        "unrelated": "keep",
    }

    clear_calculator_project_state(session_state)

    assert CALCULATOR_STATE_KEY not in session_state
    assert CALCULATOR_ADVANCED_TOGGLE_KEY not in session_state
    assert CALCULATOR_DRAFT_NAMESPACE_KEY not in session_state
    assert CALCULATOR_READY_DOWNLOAD_KEY not in session_state
    assert "calculator_grid_revision" not in session_state
    assert "calculator_grid_editor_7" not in session_state
    assert "calculator_travel_element_autocomplete_query" not in session_state
    assert session_state["unrelated"] == "keep"

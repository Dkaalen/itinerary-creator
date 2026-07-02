from __future__ import annotations

from app_modules.workflow_state import ensure_workflow_defaults, reset_workflow_state


def test_workflow_defaults_include_calculator_grid_revision() -> None:
    state: dict[str, object] = {}

    ensure_workflow_defaults(state)

    assert state["calculator_grid_revision"] == 0


def test_reset_workflow_state_clears_calculator_backup_widget_state() -> None:
    state = {
        "calculator_state": object(),
        "calculator_grid_revision": 7,
        "calculator_backup_upload": object(),
        "calculator_travel_element_autocomplete_query": "hotel",
        "calculator_travel_element_autocomplete_result_id": "lib-1",
        "raw_text_input": "Keep?",
    }

    reset_workflow_state(state)

    assert state["calculator_state"] is None
    assert state["calculator_grid_revision"] == 0
    assert "calculator_backup_upload" not in state
    assert "calculator_travel_element_autocomplete_query" not in state
    assert "calculator_travel_element_autocomplete_result_id" not in state
    assert state["raw_text_input"] == ""

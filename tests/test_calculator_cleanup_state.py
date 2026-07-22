from __future__ import annotations

from app_modules.calculator_state_keys import CALCULATOR_PENDING_IMPORT_KEY, CALCULATOR_READY_DOWNLOAD_KEY
from app_modules.workflow_state import ensure_workflow_defaults, reset_workflow_state


def test_workflow_defaults_keep_calculator_state_but_not_retired_grid_revision() -> None:
    state: dict[str, object] = {}

    ensure_workflow_defaults(state)

    assert state["calculator_state"] is None
    assert "calculator_grid_revision" not in state
    assert "calculator_show_advanced" not in state


def test_reset_workflow_state_clears_calculator_transients_and_legacy_widget_state() -> None:
    state = {
        "calculator_state": object(),
        "calculator_component_show_advanced": True,
        CALCULATOR_READY_DOWNLOAD_KEY: {"content_base64": "eGxzeA=="},
        "calculator_grid_revision": 7,
        "calculator_backup_upload": object(),
        CALCULATOR_PENDING_IMPORT_KEY: object(),
        "calculator_travel_element_autocomplete_query": "hotel",
        "calculator_travel_element_autocomplete_result_id": "lib-1",
        "raw_text_input": "Keep?",
    }

    reset_workflow_state(state)

    assert state["calculator_state"] is None
    assert "calculator_component_show_advanced" not in state
    assert CALCULATOR_READY_DOWNLOAD_KEY not in state
    assert "calculator_grid_revision" not in state
    assert "calculator_backup_upload" not in state
    assert CALCULATOR_PENDING_IMPORT_KEY not in state
    assert "calculator_travel_element_autocomplete_query" not in state
    assert "calculator_travel_element_autocomplete_result_id" not in state
    assert state["raw_text_input"] == ""

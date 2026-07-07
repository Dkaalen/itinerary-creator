from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone

import streamlit as st

from app_modules.input_generation_action import generate_supplier_itinerary
from app_modules.itinerary_name_state import clean_itinerary_name, seed_itinerary_name_input
from app_modules.itinerary_name_ui import render_itinerary_name_input
from app_modules.saved_project_file_action import prepare_saved_project_file_download
from app_modules.saved_project_generation import create_generated_baseline_project_if_named
from app_modules.workflow_result import WorkflowActionResult
from app_modules.workflow_state import reset_workflow_state
from itinerary_generation.common import group_rows_by_day
from tests.support.streamlit_stub import SessionState
from ui.output_edits import make_output_edit_state


def _clock() -> datetime:
    return datetime(2026, 3, 4, 5, 6, 7, tzinfo=timezone.utc)


def _later_clock() -> datetime:
    return datetime(2026, 3, 5, 6, 7, 8, tzinfo=timezone.utc)


def _rows() -> list[dict]:
    return [
        {
            "day": "Day 1",
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Oslo",
            "title": "Oslo Fjord Cruise",
            "client_description": "Generated supplier description",
            "row_id": "row-1",
            "line_number": 1,
        }
    ]


def _generated_state() -> dict:
    rows = _rows()
    edits = make_output_edit_state(rows, group_rows_by_day(rows))
    edits["output_brand"] = "booknordics_customer"
    edits["trip_title"] = "Generated Trip Title"
    return {
        "last_generated_raw_text": "Day 1\tActivity\tOslo Fjord Cruise",
        "raw_text_input": "Day 1\tActivity\tOslo Fjord Cruise",
        "parsed_rows": rows,
        "output_edits": edits,
        "detail_level": "Rich descriptive",
        "day_page_layout": "One day per page",
        "pdf_status": "Not created",
    }


def test_itinerary_name_is_cleaned_for_project_metadata() -> None:
    assert clean_itinerary_name("  Norway   Winter Group   -   Jan 2027  ") == "Norway Winter Group - Jan 2027"


def test_name_input_seeds_from_loaded_project_name(monkeypatch) -> None:
    st.session_state = SessionState({"itinerary_name": "Saved Oslo Project"})
    calls: list[dict] = []
    monkeypatch.setattr(st, "text_input", lambda *args, **kwargs: calls.append({"args": args, "kwargs": kwargs}), raising=False)

    render_itinerary_name_input()

    assert st.session_state["itinerary_name_input"] == "Saved Oslo Project"
    assert calls[0]["args"] == ("Itinerary name",)
    assert calls[0]["kwargs"]["key"] == "itinerary_name_input"


def test_named_generation_creates_baseline_project_equal_to_current_snapshot() -> None:
    state = _generated_state()
    state["itinerary_name_input"] = "  Norway Winter Group - Jan 2027  "

    created = create_generated_baseline_project_if_named(state)

    assert created is True
    assert state["itinerary_name"] == "Norway Winter Group - Jan 2027"
    payload = state["active_saved_project"]
    assert payload["metadata"]["itinerary_name"] == "Norway Winter Group - Jan 2027"
    assert payload["metadata"]["project_id"] == state["active_saved_project_id"]
    assert payload["generated_baseline_snapshot"] == payload["current_snapshot"]
    assert payload["generated_baseline_snapshot"]["parsed_rows"] == _rows()


def test_unnamed_generation_remains_unsaved_and_save_file_still_works_later() -> None:
    state = _generated_state()
    state["active_saved_project"] = {"stale": True}
    state["active_saved_project_id"] = "stale-project"
    state["itinerary_name_input"] = "   "

    created = create_generated_baseline_project_if_named(state)

    assert created is False
    assert state["itinerary_name"] == ""
    assert "active_saved_project" not in state
    assert "active_saved_project_id" not in state

    project_file = prepare_saved_project_file_download(state, clock=_clock)
    payload = json.loads(project_file.data.decode("utf-8"))

    assert payload["metadata"]["itinerary_name"] == ""
    assert payload["kind"] == "itinerary_project"
    assert state["active_saved_project_id"] == payload["metadata"]["project_id"]


def test_save_after_named_baseline_updates_current_without_overwriting_baseline() -> None:
    state = _generated_state()
    state["itinerary_name_input"] = "Norway Winter Group"
    create_generated_baseline_project_if_named(state)
    baseline_payload = deepcopy(state["active_saved_project"])

    state["output_edits"] = deepcopy(state["output_edits"])
    state["output_edits"]["rows"]["row-1"]["title"] = "Edited cruise title"
    project_file = prepare_saved_project_file_download(state, clock=_later_clock)
    payload = json.loads(project_file.data.decode("utf-8"))

    assert payload["metadata"]["project_id"] == baseline_payload["metadata"]["project_id"]
    assert payload["metadata"]["itinerary_name"] == "Norway Winter Group"
    assert payload["generated_baseline_snapshot"] == baseline_payload["generated_baseline_snapshot"]
    assert payload["current_snapshot"] != payload["generated_baseline_snapshot"]
    assert payload["current_snapshot"]["output_edits"]["rows"]["row-1"]["title"] == "Edited cruise title"


def test_generate_button_syncs_itinerary_name_before_shared_pipeline(monkeypatch) -> None:
    st.session_state = SessionState({"itinerary_name_input": "  Norway Winter Group  "})
    calls: list[tuple[dict, str]] = []

    def fake_generate_itinerary(state, raw_text):
        calls.append((dict(state), raw_text))
        return WorkflowActionResult(ok=True, stage="edit", message="ok")

    monkeypatch.setattr("app_modules.input_generation_action.generate_itinerary", fake_generate_itinerary)

    assert generate_supplier_itinerary(st.session_state, "raw supplier rows", "agent") is True

    assert st.session_state["itinerary_name"] == "Norway Winter Group"
    assert st.session_state["requested_output_brand"] == "agent"
    assert calls[0][1] == "raw supplier rows"
    assert calls[0][0]["itinerary_name"] == "Norway Winter Group"


def test_reset_clears_itinerary_name_input_state() -> None:
    state = {
        "itinerary_name": "Saved Trip",
        "itinerary_name_input": "Saved Trip",
        "raw_text_input": "raw",
        "parsed_rows": _rows(),
    }

    reset_workflow_state(state, clear_raw_text=True)

    assert state["raw_text_input"] == ""
    assert "itinerary_name" not in state
    assert "itinerary_name_input" not in state


def test_seed_itinerary_name_input_does_not_overwrite_current_input() -> None:
    state = SessionState({"itinerary_name": "Saved Trip", "itinerary_name_input": "Draft Name"})

    seed_itinerary_name_input(state)

    assert state["itinerary_name_input"] == "Draft Name"

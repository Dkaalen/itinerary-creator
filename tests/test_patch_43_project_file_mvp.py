from __future__ import annotations

import io
import json
from copy import deepcopy
from datetime import datetime, timezone

import streamlit as st

from app_modules.project_io import load_project_json
from app_modules.saved_project_builder import build_saved_project_from_state
from app_modules.saved_project_file_action import PROJECT_FILE_SUFFIX, prepare_saved_project_file_download
from app_modules.saved_project_serialization import saved_project_to_dict
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
            "date": "01/01/2027",
            "start_date": "01/01/2027",
        }
    ]


def _generated_state() -> dict:
    rows = _rows()
    edits = make_output_edit_state(rows, group_rows_by_day(rows))
    edits["output_brand"] = "booknordics_customer"
    edits["trip_title"] = "Norway Winter Group"
    edits["cover_image"] = {"mode": "manual", "path": "images/cover.webp", "data_uri": "data:image/png;base64,AAA"}
    edits["day_images"] = {"Day 1": {"mode": "manual", "path": "images/oslo.webp", "preview_data_uri": "bad"}}
    edits["pictures_added"] = True
    return {
        "last_generated_raw_text": "Day 1\tActivity\tOslo Fjord Cruise",
        "raw_text_input": "Day 1\tActivity\tOslo Fjord Cruise",
        "parsed_rows": rows,
        "output_edits": edits,
        "detail_level": "Rich descriptive",
        "day_page_layout": "One day per page",
        "pdf_status": "Needs refresh",
        "itinerary_html": "<html>must not be saved</html>",
        "pdf_bytes": b"%PDF",
    }


def test_project_file_download_serializes_valid_saved_project_without_preview_bloat() -> None:
    state = _generated_state()

    project_file = prepare_saved_project_file_download(state, clock=_clock)
    payload = json.loads(project_file.data.decode("utf-8"))
    encoded = project_file.data.decode("utf-8")

    assert project_file.file_name == f"norway_winter_group{PROJECT_FILE_SUFFIX}"
    assert payload["kind"] == "itinerary_project"
    assert payload["metadata"]["project_id"] == state["active_saved_project_id"]
    assert payload["current_snapshot"]["parsed_rows"] == _rows()
    assert "itinerary_html" not in encoded
    assert "pdf_bytes" not in encoded
    assert "data:image" not in encoded
    assert "preview_data_uri" not in encoded


def test_project_file_save_updates_current_snapshot_without_overwriting_baseline() -> None:
    state = _generated_state()
    first_file = prepare_saved_project_file_download(state, clock=_clock)
    first_payload = json.loads(first_file.data.decode("utf-8"))

    state["output_edits"] = deepcopy(state["output_edits"])
    state["output_edits"]["rows"]["row-1"]["title"] = "Edited saved cruise title"
    second_file = prepare_saved_project_file_download(state, clock=_later_clock)
    second_payload = json.loads(second_file.data.decode("utf-8"))

    assert second_payload["metadata"]["project_id"] == first_payload["metadata"]["project_id"]
    assert second_payload["metadata"]["created_at"] == "2026-03-04T05:06:07Z"
    assert second_payload["metadata"]["updated_at"] == "2026-03-05T06:07:08Z"
    assert second_payload["generated_baseline_snapshot"] == first_payload["generated_baseline_snapshot"]
    assert second_payload["current_snapshot"]["output_edits"]["rows"]["row-1"]["title"] == "Edited saved cruise title"


def test_open_project_file_reopens_saved_project_without_pasting_source() -> None:
    st.session_state = SessionState()
    project = build_saved_project_from_state(_generated_state(), itinerary_name="Saved Oslo", clock=_clock)
    payload = json.dumps(saved_project_to_dict(project)).encode("utf-8")

    assert load_project_json(io.BytesIO(payload), require_saved_project=True) is True

    assert st.session_state["parsed_rows"] == _rows()
    assert st.session_state["raw_text_input"] == "Day 1\tActivity\tOslo Fjord Cruise"
    assert st.session_state["active_saved_project_id"] == project.metadata.project_id
    assert st.session_state["app_stage"] == "pictures"
    assert st.session_state["itinerary_html"]


def test_open_project_file_reports_invalid_json_without_traceback(monkeypatch) -> None:
    st.session_state = SessionState()
    errors: list[str] = []
    exceptions: list[Exception] = []
    monkeypatch.setattr(st, "error", lambda message: errors.append(str(message)))
    monkeypatch.setattr(st, "exception", lambda error: exceptions.append(error))

    assert load_project_json(io.BytesIO(b"not json"), require_saved_project=True) is False

    assert errors == ["The project file is not valid JSON."]
    assert exceptions == []


def test_open_project_file_reports_wrong_schema_safely(monkeypatch) -> None:
    st.session_state = SessionState()
    payload = saved_project_to_dict(build_saved_project_from_state(_generated_state(), clock=_clock))
    payload["saved_schema_version"] = 999
    errors: list[str] = []
    monkeypatch.setattr(st, "error", lambda message: errors.append(str(message)))

    assert load_project_json(io.BytesIO(json.dumps(payload).encode("utf-8")), require_saved_project=True) is False

    assert errors
    assert "Unsupported saved project schema version" in errors[0]


def test_save_project_file_ui_renders_download_button(monkeypatch) -> None:
    import app_modules.project_file_ui as project_file_ui

    st.session_state = SessionState(_generated_state())
    calls: list[dict] = []
    monkeypatch.setattr(project_file_ui.st, "download_button", lambda **kwargs: calls.append(kwargs), raising=False)

    project_file_ui.render_save_project_file_action(key_suffix="test")

    assert len(calls) == 1
    assert calls[0]["label"] == "Download backup file"
    assert calls[0]["file_name"].endswith(PROJECT_FILE_SUFFIX)
    assert calls[0]["mime"] == "application/json"
    assert json.loads(calls[0]["data"].decode("utf-8"))["kind"] == "itinerary_project"


def test_reset_project_state_clears_active_project_file_metadata() -> None:
    state = _generated_state()
    prepare_saved_project_file_download(state, clock=_clock)

    reset_workflow_state(state, clear_raw_text=True)

    assert state["parsed_rows"] == []
    assert state["raw_text_input"] == ""
    assert "active_saved_project" not in state
    assert "active_saved_project_id" not in state
    assert "itinerary_name" not in state

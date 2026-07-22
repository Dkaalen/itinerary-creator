from __future__ import annotations

import io
import json
from copy import deepcopy
from datetime import datetime, timezone

import streamlit as st

from app_modules.calculator_navigation import calculator_draft_namespace
from app_modules.project_io import load_project_json
from app_modules.project_file_download_cache import PROJECT_FILE_DOWNLOAD_CACHE_KEY
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


def test_open_project_file_reopens_as_fresh_unsaved_project_without_pasting_source(monkeypatch) -> None:
    st.session_state = SessionState(
        {
            "active_saved_project_id": "cloud-old",
            "active_project_storage_id": "cloud-old",
            "project_storage_last_saved_snapshot_path": "cloud-old/agent/v1.json",
            "project_storage_last_calculator_file_path": "cloud-old/calculation.xlsx",
            "project_storage_last_calculator_snapshot": {"rows": [{"row_id": "old"}]},
            "project_storage_last_pdf_path": "cloud-old/agent/itinerary.pdf",
            "project_storage_last_error": "old error",
            "project_storage_last_error_detail": "old detail",
            "calculator_draft_namespace": "project:cloud-old",
            "cloud_calculator_file_payload_old": b"xlsx",
            "open_project_selected_project_id": "cloud-old",
            "open_project_delete_candidate_id": "cloud-old",
            "open_project_rename_candidate_id": "cloud-old",
            "open_project_unsaved_open_candidate_id": "cloud-old",
            "open_project_file_delete_candidate_id": "file-old",
            PROJECT_FILE_DOWNLOAD_CACHE_KEY: {"signature": "old", "payload": b"json"},
        }
    )
    project = build_saved_project_from_state(_generated_state(), itinerary_name="Saved Oslo", clock=_clock)
    payload = json.dumps(saved_project_to_dict(project)).encode("utf-8")
    monkeypatch.setattr("app_modules.project_io.uuid4", lambda: "fresh-local-project")

    assert load_project_json(io.BytesIO(payload), require_saved_project=True) is True

    assert st.session_state["parsed_rows"] == _rows()
    assert st.session_state["raw_text_input"] == "Day 1\tActivity\tOslo Fjord Cruise"
    assert st.session_state["active_saved_project_id"] == "fresh-local-project"
    assert st.session_state["active_project_storage_id"] == "fresh-local-project"
    assert st.session_state["active_saved_project"]["metadata"]["project_id"] == "fresh-local-project"
    assert calculator_draft_namespace(st.session_state) == "project:fresh-local-project"
    assert st.session_state["app_stage"] == "pictures"
    assert st.session_state["itinerary_html"]
    assert "project_storage_last_saved_snapshot_path" not in st.session_state
    assert "project_storage_last_calculator_file_path" not in st.session_state
    assert "project_storage_last_calculator_snapshot" not in st.session_state
    assert "project_storage_last_pdf_path" not in st.session_state
    assert "project_storage_last_error" not in st.session_state
    assert "project_storage_last_error_detail" not in st.session_state
    assert "cloud_calculator_file_payload_old" not in st.session_state
    assert "open_project_selected_project_id" not in st.session_state
    assert "open_project_delete_candidate_id" not in st.session_state
    assert "open_project_rename_candidate_id" not in st.session_state
    assert "open_project_unsaved_open_candidate_id" not in st.session_state
    assert "open_project_file_delete_candidate_id" not in st.session_state
    assert PROJECT_FILE_DOWNLOAD_CACHE_KEY not in st.session_state



def test_failed_backup_open_preserves_existing_cloud_identity_and_markers(monkeypatch) -> None:
    existing_project = build_saved_project_from_state(_generated_state(), itinerary_name="Existing", clock=_clock)
    st.session_state = SessionState(
        {
            "active_saved_project_id": "cloud-existing",
            "active_project_storage_id": "cloud-existing",
            "active_saved_project": saved_project_to_dict(existing_project),
            "project_storage_last_saved_snapshot_path": "cloud-existing/agent/v1.json",
            "project_storage_last_calculator_file_path": "cloud-existing/calculation.xlsx",
            "calculator_draft_namespace": "project:cloud-existing",
        }
    )
    invalid = saved_project_to_dict(build_saved_project_from_state(_generated_state(), clock=_clock))
    invalid["saved_schema_version"] = 999
    monkeypatch.setattr("app_modules.project_io.uuid4", lambda: "unused-fresh-id")
    errors: list[str] = []
    monkeypatch.setattr(st, "error", lambda message: errors.append(str(message)))

    assert load_project_json(io.BytesIO(json.dumps(invalid).encode("utf-8")), require_saved_project=True) is False

    assert st.session_state["active_saved_project_id"] == "cloud-existing"
    assert st.session_state["active_project_storage_id"] == "cloud-existing"
    assert st.session_state["project_storage_last_saved_snapshot_path"] == "cloud-existing/agent/v1.json"
    assert st.session_state["project_storage_last_calculator_file_path"] == "cloud-existing/calculation.xlsx"
    assert st.session_state["calculator_draft_namespace"] == "project:cloud-existing"
    assert errors


def test_cloud_project_open_override_preserves_cloud_identity() -> None:
    state = SessionState()
    project = build_saved_project_from_state(_generated_state(), itinerary_name="Cloud Oslo", clock=_clock)

    from app_modules.saved_project_load_action import load_saved_project

    result = load_saved_project(state, saved_project_to_dict(project), project_id_override="cloud-project-123")

    assert result.ok is True
    assert state["active_saved_project_id"] == "cloud-project-123"
    assert state["active_project_storage_id"] == "cloud-project-123"
    assert state["active_saved_project"]["metadata"]["project_id"] == "cloud-project-123"

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
    import app_modules.project_save_ui as project_save_ui

    st.session_state = SessionState(_generated_state())
    calls: list[dict] = []
    monkeypatch.setattr(project_save_ui.st, "download_button", lambda **kwargs: calls.append(kwargs), raising=False)

    project_save_ui.render_save_project_file_action(key_suffix="test")

    assert len(calls) == 1
    assert calls[0]["label"] == "Download backup file"
    assert calls[0]["file_name"].endswith(PROJECT_FILE_SUFFIX)
    assert calls[0]["mime"] == "application/json"
    assert json.loads(calls[0]["data"].decode("utf-8"))["kind"] == "itinerary_project"


def test_reset_project_state_clears_active_project_file_metadata() -> None:
    state = _generated_state()
    state["pending_project_backup_import"] = object()
    prepare_saved_project_file_download(state, clock=_clock)

    reset_workflow_state(state, clear_raw_text=True)

    assert state["parsed_rows"] == []
    assert state["raw_text_input"] == ""
    assert "active_saved_project" not in state
    assert "active_saved_project_id" not in state
    assert "itinerary_name" not in state
    assert "pending_project_backup_import" not in state

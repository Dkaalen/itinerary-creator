from __future__ import annotations

import json
from datetime import datetime, timezone

import streamlit as st

from app_modules.saved_project_file_action import prepare_saved_project_file_download
from app_modules.saved_project_storage_decision import (
    BACKLOG_ACTIONS,
    CLOUD_BACKLOG_MODE,
    PROJECT_FILE_STORAGE_MODE,
    assert_project_file_mode_payload,
    enabled_backlog_actions,
    get_saved_project_storage_decision,
    saved_project_backlog_is_enabled,
)
from itinerary_generation.common import group_rows_by_day
from tests.support.streamlit_stub import SessionState
from ui.output_edits import make_output_edit_state


class _Container:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _clock() -> datetime:
    return datetime(2026, 5, 1, 2, 3, 4, tzinfo=timezone.utc)


def _generated_state() -> dict:
    rows = [
        {
            "day": "Day 1",
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Oslo",
            "title": "Oslo Fjord Cruise",
            "client_description": "Generated description",
            "row_id": "row-1",
            "line_number": 1,
            "date": "01/01/2027",
            "start_date": "01/01/2027",
        }
    ]
    edits = make_output_edit_state(rows, group_rows_by_day(rows))
    edits["trip_title"] = "Norway Project File"
    return {
        "last_generated_raw_text": "Day 1\tActivity\tOslo Fjord Cruise",
        "raw_text_input": "Day 1\tActivity\tOslo Fjord Cruise",
        "parsed_rows": rows,
        "output_edits": edits,
        "detail_level": "Rich descriptive",
        "day_page_layout": "One day per page",
        "pdf_status": "Not created",
    }


def test_keeps_project_file_as_only_enabled_storage_mode() -> None:
    decision = get_saved_project_storage_decision()

    assert decision.mode == PROJECT_FILE_STORAGE_MODE
    assert decision.label == "Project File mode"
    assert decision.backlog_enabled is False
    assert decision.browser_private_backlog_enabled is False
    assert decision.search_index_enabled is False
    assert decision.cloud_backend_enabled is False
    assert decision.future_cloud_backend_unblocked is True
    assert saved_project_backlog_is_enabled() is False
    assert enabled_backlog_actions() == ()
    assert BACKLOG_ACTIONS == ("open", "duplicate", "rename", "archive")


def test_storage_decision_remains_cloud_ready_without_enabling_cloud_storage() -> None:
    decision_payload = get_saved_project_storage_decision().to_dict()

    assert decision_payload["mode"] == PROJECT_FILE_STORAGE_MODE
    assert decision_payload["future_cloud_backend_unblocked"] is True
    assert CLOUD_BACKLOG_MODE != decision_payload["mode"]
    assert "database" not in decision_payload
    assert "st.session_state" not in str(decision_payload)


def test_project_file_payload_has_no_backlog_or_search_index_storage() -> None:
    state = _generated_state()
    project_file = prepare_saved_project_file_download(state, clock=_clock)
    payload = json.loads(project_file.data.decode("utf-8"))
    encoded = json.dumps(payload).lower()

    assert payload["kind"] == "itinerary_project"
    assert "saved_project_backlog" not in encoded
    assert "saved_project_search_index" not in encoded
    assert "indexeddb" not in encoded
    assert "localstorage" not in encoded
    assert "archive" not in encoded


def test_project_file_guard_rejects_accidental_backlog_payload() -> None:
    try:
        assert_project_file_mode_payload({"metadata": {"saved_project_search_index": []}})
    except ValueError as error:
        assert "saved_project_search_index" in str(error)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected backlog/search-index payload to be rejected")


def test_open_project_ui_renders_storage_note_without_backlog_controls(monkeypatch) -> None:
    import app_modules.project_browser_ui as project_browser_ui

    st.session_state = SessionState()
    captions: list[str] = []
    labels: list[str] = []
    upload_labels: list[str] = []
    button_calls = iter((True, False))
    monkeypatch.setattr(project_browser_ui.st, "container", lambda **kwargs: _Container(), raising=False)
    monkeypatch.setattr(project_browser_ui.st, "html", lambda value: labels.append(str(value)), raising=False)
    monkeypatch.setattr(project_browser_ui.st, "caption", lambda value: captions.append(str(value)), raising=False)
    monkeypatch.setattr(project_browser_ui.st, "button", lambda *args, **kwargs: next(button_calls, False), raising=False)
    monkeypatch.setattr(
        project_browser_ui.st,
        "file_uploader",
        lambda label, *args, **kwargs: upload_labels.append(str(label)) or None,
        raising=False,
    )

    project_browser_ui.render_open_project_file_action()
    project_browser_ui.render_open_project_workspace_if_visible()
    rendered = "\n".join(labels + captions + upload_labels)

    assert "Project Explorer" in rendered
    assert ".itinerary.json" in rendered
    assert "Search" not in rendered
    assert "Duplicate" not in rendered
    assert "Rename" not in rendered
    assert "Archive" not in rendered

from __future__ import annotations

from app_modules.project_browser_state import (
    clear_delete_confirmation,
    delete_candidate_id,
    remember_delete_candidate,
)
from app_modules.project_delete_cleanup import clear_deleted_project_from_session


def test_delete_confirmation_state_has_single_owner() -> None:
    state: dict[str, object] = {}

    remember_delete_candidate(state, project_id="project-1", name="Norway Winter")

    assert delete_candidate_id(state) == "project-1"
    assert state["open_project_delete_candidate_name"] == "Norway Winter"

    clear_delete_confirmation(state)

    assert delete_candidate_id(state) == ""
    assert "open_project_delete_candidate_name" not in state


def test_clear_deleted_project_from_session_only_clears_active_project() -> None:
    state: dict[str, object] = {
        "active_project_storage_id": "active-1",
        "active_saved_project_id": "active-1",
        "active_saved_project": {"metadata": {"project_id": "active-1"}},
        "project_storage_last_saved_snapshot_path": "snapshots/latest.json",
        "project_storage_last_calculator_file_path": "calculator/latest.xlsx",
        "project_storage_last_pdf_path": "pdf/latest.pdf",
        "project_storage_last_calculator_snapshot": {"rows": []},
        "project_storage_last_error": "bad",
        "project_storage_last_error_detail": "technical",
        "cloud_calculator_file_payload_active-1_0": b"xlsx",
        "_project_file_download_cache": {"payload": b"json"},
        "day_image_matches": {"Day 1": {"path": "old.jpg"}},
    }

    clear_deleted_project_from_session(state, "other-1")

    assert state["active_project_storage_id"] == "active-1"
    assert state["active_saved_project_id"] == "active-1"

    clear_deleted_project_from_session(state, "active-1")

    assert "active_project_storage_id" not in state
    assert "active_saved_project_id" not in state
    assert "active_saved_project" not in state
    assert "project_storage_last_saved_snapshot_path" not in state
    assert "project_storage_last_calculator_file_path" not in state
    assert "project_storage_last_pdf_path" not in state
    assert "project_storage_last_calculator_snapshot" not in state
    assert "project_storage_last_error" not in state
    assert "project_storage_last_error_detail" not in state
    assert "cloud_calculator_file_payload_active-1_0" not in state
    assert "_project_file_download_cache" not in state
    assert "day_image_matches" not in state

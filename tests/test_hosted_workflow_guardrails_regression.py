from __future__ import annotations

from pathlib import Path

from app_modules.calculator_navigation import (
    CALCULATOR_DRAFT_NAMESPACE_KEY,
    calculator_draft_namespace,
    open_calculator_page,
)
from app_modules.workflow_state import reset_workflow_state
from app_modules.workflow_transients import clear_project_boundary_transients


def _calculator_js_bundle_source() -> str:
    frontend_dir = Path("calculator_grid_component/frontend/js")
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(frontend_dir.glob("calculator_grid_*.js")))


def test_project_boundary_cleanup_removes_stale_browser_transaction_state() -> None:
    state = {
        "_visual_editor_commit_nonce": "12",
        "_pdf_after_visual_edit_commit_nonce": "12",
        "_pdf_after_visual_edit_commit_requested_at": 100.0,
        "_add_pictures_after_visual_edit_commit_nonce": "13",
        "_add_pictures_after_visual_edit_commit_requested_at": 101.0,
        "_pdf_auto_create_requested": True,
        "_pdf_export_job": {"state": "saving"},
        "_image_bank_status_cache": {"status": {}},
        "add_pictures_last_error": "stale",
        "parsed_rows": [{"day": "Day 1"}],
    }

    clear_project_boundary_transients(state)

    assert state["parsed_rows"] == [{"day": "Day 1"}]
    for key in (
        "_visual_editor_commit_nonce",
        "_pdf_after_visual_edit_commit_nonce",
        "_pdf_after_visual_edit_commit_requested_at",
        "_add_pictures_after_visual_edit_commit_nonce",
        "_add_pictures_after_visual_edit_commit_requested_at",
        "_pdf_auto_create_requested",
        "_pdf_export_job",
        "_image_bank_status_cache",
        "add_pictures_last_error",
    ):
        assert key not in state


def test_full_reset_clears_calculator_namespace_and_pending_workflow_state() -> None:
    state = {
        "calculator_draft_namespace": "session:old",
        "_pdf_after_visual_edit_commit_requested_at": 10.0,
        "_add_pictures_after_visual_edit_commit_requested_at": 11.0,
        "raw_text_input": "keep?",
    }

    reset_workflow_state(state, clear_raw_text=True)

    assert state["raw_text_input"] == ""
    assert "calculator_draft_namespace" not in state
    assert "_pdf_after_visual_edit_commit_requested_at" not in state
    assert "_add_pictures_after_visual_edit_commit_requested_at" not in state
    assert state["app_stage"] == "input"


def test_calculator_draft_namespace_is_stable_for_unsaved_name_edits() -> None:
    state = {"itinerary_name": "First name"}

    first = calculator_draft_namespace(state)
    state["itinerary_name"] = "Renamed itinerary"
    second = calculator_draft_namespace(state)

    assert first.startswith("session:")
    assert second == first
    assert state[CALCULATOR_DRAFT_NAMESPACE_KEY] == first


def test_calculator_draft_namespace_switches_to_saved_project_id() -> None:
    state = {"calculator_draft_namespace": "session:old", "active_saved_project_id": "project-123"}

    assert calculator_draft_namespace(state) == "project:project-123"
    open_calculator_page(state)
    assert state[CALCULATOR_DRAFT_NAMESPACE_KEY] == "project:project-123"


def test_detached_cloud_workspace_gets_a_new_unsaved_draft_namespace() -> None:
    from app_modules.project_session_cleanup import clear_active_cloud_project_session

    state = {
        "active_saved_project_id": "project-123",
        "active_project_storage_id": "project-123",
        CALCULATOR_DRAFT_NAMESPACE_KEY: "project:project-123",
    }

    clear_active_cloud_project_session(state)
    replacement = calculator_draft_namespace(state)

    assert replacement.startswith("session:")
    assert replacement != "project:project-123"


def test_calculator_frontend_resets_browser_draft_when_namespace_changes() -> None:
    source = _calculator_js_bundle_source()

    assert "activeDraftStorageKey" in source
    assert "incomingDraftStorageKey === activeDraftStorageKey" in source
    assert "window.ItineraryCalculator.storage.getDraftStorageKey" in source
    assert "return draftStorageKey;" in source

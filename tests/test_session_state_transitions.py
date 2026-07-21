from __future__ import annotations

from app_modules.calculator_state_keys import CALCULATOR_RETURN_AVAILABLE_KEY
from app_modules.project_identity import active_project_id_from_state
from app_modules.project_save_rollback import capture_project_save_baseline
from app_modules.session_state_keys import (
    ACTIVE_APP_PAGE_KEY,
    ACTIVE_PROJECT_STORAGE_ID_KEY,
    ACTIVE_SAVED_PROJECT_ID_KEY,
    ACTIVE_SAVED_PROJECT_KEY,
    APP_STAGE_KEY,
    CALCULATOR_PAGE,
    OPEN_PROJECT_BROWSER_VISIBLE_KEY,
    PROJECT_STORAGE_BROWSER_SUCCESS_KEY,
    PROJECT_STORAGE_DELETE_CLEANUP_WARNING_KEY,
    PROJECT_STORAGE_LAST_ERROR_DETAIL_KEY,
    PROJECT_STORAGE_LAST_ERROR_KEY,
    WORKFLOW_PAGE,
)
from app_modules.session_transitions import (
    begin_local_calculator_import,
    complete_calculator_generation,
    complete_project_delete,
    complete_project_duplicate,
    complete_saved_project_open,
    fail_calculator_generation,
    record_failed_save,
)


def test_local_calculator_import_detaches_cloud_identity_and_keeps_calculator_active() -> None:
    state = {
        ACTIVE_APP_PAGE_KEY: WORKFLOW_PAGE,
        ACTIVE_SAVED_PROJECT_KEY: {"metadata": {"project_id": "old"}},
        ACTIVE_PROJECT_STORAGE_ID_KEY: "old",
        ACTIVE_SAVED_PROJECT_ID_KEY: "old",
        CALCULATOR_RETURN_AVAILABLE_KEY: True,
    }

    begin_local_calculator_import(state)

    assert state[ACTIVE_APP_PAGE_KEY] == CALCULATOR_PAGE
    assert active_project_id_from_state(state) == ""
    assert ACTIVE_SAVED_PROJECT_KEY not in state
    assert CALCULATOR_RETURN_AVAILABLE_KEY not in state


def test_calculator_generation_transitions_preserve_expected_route_and_stage() -> None:
    state = {ACTIVE_APP_PAGE_KEY: CALCULATOR_PAGE, APP_STAGE_KEY: "pictures"}

    complete_calculator_generation(state)

    assert state[ACTIVE_APP_PAGE_KEY] == WORKFLOW_PAGE
    assert state[CALCULATOR_RETURN_AVAILABLE_KEY] is True

    restored = fail_calculator_generation(state, "pictures")

    assert restored == "pictures"
    assert state[APP_STAGE_KEY] == "pictures"
    assert state[ACTIVE_APP_PAGE_KEY] == CALCULATOR_PAGE


def test_saved_project_open_commits_one_coherent_identity_and_closes_browser() -> None:
    state = {
        ACTIVE_APP_PAGE_KEY: CALCULATOR_PAGE,
        OPEN_PROJECT_BROWSER_VISIBLE_KEY: True,
        ACTIVE_PROJECT_STORAGE_ID_KEY: "old",
        ACTIVE_SAVED_PROJECT_ID_KEY: "old",
    }
    payload = {"metadata": {"project_id": "new", "itinerary_name": "New project"}}

    complete_saved_project_open(state, project_payload=payload, project_id="new")

    assert state[ACTIVE_SAVED_PROJECT_KEY] == payload
    assert active_project_id_from_state(state) == "new"
    assert state[ACTIVE_PROJECT_STORAGE_ID_KEY] == "new"
    assert state[ACTIVE_SAVED_PROJECT_ID_KEY] == "new"
    assert state[ACTIVE_APP_PAGE_KEY] == WORKFLOW_PAGE
    assert state[OPEN_PROJECT_BROWSER_VISIBLE_KEY] is False


def test_duplicate_and_delete_transitions_own_browser_messages_and_active_cleanup() -> None:
    state = {
        ACTIVE_SAVED_PROJECT_KEY: {"metadata": {"project_id": "project-1"}},
        ACTIVE_PROJECT_STORAGE_ID_KEY: "project-1",
        ACTIVE_SAVED_PROJECT_ID_KEY: "project-1",
    }

    complete_project_duplicate(state, name="Project copy")
    assert state[PROJECT_STORAGE_BROWSER_SUCCESS_KEY] == "Created Project copy."

    complete_project_delete(
        state,
        project_id="project-1",
        name="Project one",
        storage_files_deleted=False,
    )

    assert active_project_id_from_state(state) == ""
    assert ACTIVE_SAVED_PROJECT_KEY not in state
    assert state[PROJECT_STORAGE_BROWSER_SUCCESS_KEY] == "Deleted Project one."
    assert "stored files" in state[PROJECT_STORAGE_DELETE_CLEANUP_WARNING_KEY]


def test_failed_save_transition_restores_identity_before_recording_error() -> None:
    state = {
        ACTIVE_SAVED_PROJECT_KEY: {"metadata": {"project_id": "before"}},
        ACTIVE_PROJECT_STORAGE_ID_KEY: "before",
        ACTIVE_SAVED_PROJECT_ID_KEY: "before",
        "itinerary_name": "Before",
    }
    baseline = capture_project_save_baseline(state)
    state[ACTIVE_SAVED_PROJECT_KEY] = {"metadata": {"project_id": "partial"}}
    state[ACTIVE_PROJECT_STORAGE_ID_KEY] = "partial"
    state[ACTIVE_SAVED_PROJECT_ID_KEY] = "partial"
    state["itinerary_name"] = "Partial"

    record_failed_save(
        state,
        baseline=baseline,
        user_message="Save failed.",
        technical_detail="database timeout",
    )

    assert active_project_id_from_state(state) == "before"
    assert state["itinerary_name"] == "Before"
    assert state[PROJECT_STORAGE_LAST_ERROR_KEY] == "Save failed."
    assert state[PROJECT_STORAGE_LAST_ERROR_DETAIL_KEY] == "database timeout"


def test_saved_project_open_rolls_back_all_tracked_state_when_rebuild_fails(monkeypatch) -> None:
    from datetime import datetime, timezone

    import app_modules.saved_project_load_action as load_action
    import app_modules.saved_project_restore as restore_action
    from app_modules.saved_project_builder import build_saved_project_from_state
    from itinerary_generation.common import group_rows_by_day
    from ui.output_edits import make_output_edit_state

    rows = [
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
    edits = make_output_edit_state(rows, group_rows_by_day(rows))
    source_state = {
        "last_generated_raw_text": "Day 1\tActivity\tOslo Fjord Cruise",
        "raw_text_input": "Day 1\tActivity\tOslo Fjord Cruise",
        "parsed_rows": rows,
        "output_edits": edits,
        "detail_level": "Rich descriptive",
        "day_page_layout": "One day per page",
    }
    project = build_saved_project_from_state(
        source_state,
        itinerary_name="Replacement",
        project_id="replacement-id",
        clock=lambda: datetime(2026, 7, 21, tzinfo=timezone.utc),
    )
    state = {
        ACTIVE_APP_PAGE_KEY: CALCULATOR_PAGE,
        APP_STAGE_KEY: "pictures",
        ACTIVE_SAVED_PROJECT_KEY: {"metadata": {"project_id": "original-id"}},
        ACTIVE_PROJECT_STORAGE_ID_KEY: "original-id",
        ACTIVE_SAVED_PROJECT_ID_KEY: "original-id",
        "itinerary_name": "Original",
        "parsed_rows": [{"day": "Day 1", "title": "Original row"}],
        "output_edits": {"trip_title": "Original"},
        "pdf_bytes": b"original-pdf",
        "calculator_ready_xlsx_download": {"filename": "original.xlsx"},
        "calculator_itinerary_name_sync_required": False,
    }
    before = dict(state)
    monkeypatch.setattr(restore_action, "rebuild_restored_preview", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))

    try:
        load_action.load_saved_project(state, project)
    except RuntimeError as error:
        assert str(error) == "boom"
    else:
        raise AssertionError("Expected rebuild failure")

    assert state[ACTIVE_APP_PAGE_KEY] == before[ACTIVE_APP_PAGE_KEY]
    assert state[APP_STAGE_KEY] == before[APP_STAGE_KEY]
    assert state[ACTIVE_SAVED_PROJECT_KEY] == before[ACTIVE_SAVED_PROJECT_KEY]
    assert active_project_id_from_state(state) == "original-id"
    assert state["itinerary_name"] == "Original"
    assert state["parsed_rows"] == before["parsed_rows"]
    assert state["output_edits"] == before["output_edits"]
    assert state["pdf_bytes"] == b"original-pdf"
    assert state["calculator_ready_xlsx_download"] == {"filename": "original.xlsx"}
    assert state["calculator_itinerary_name_sync_required"] is False

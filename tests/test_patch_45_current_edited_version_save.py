from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

from app_modules.saved_project_builder import build_saved_project_from_state
from app_modules.saved_project_current_state import refresh_active_saved_project_current_snapshot
from app_modules.saved_project_file_action import prepare_saved_project_file_download
from app_modules.saved_project_load_action import load_saved_project
from app_modules.saved_project_serialization import saved_project_from_dict, saved_project_to_dict
from app_modules.saved_project_update import update_saved_project_current_snapshot
from itinerary_generation.common import group_rows_by_day
from ui.output_edits import make_output_edit_state


def _clock() -> datetime:
    return datetime(2026, 4, 1, 2, 3, 4, tzinfo=timezone.utc)


def _later_clock() -> datetime:
    return datetime(2026, 4, 2, 3, 4, 5, tzinfo=timezone.utc)


def _export_clock() -> datetime:
    return datetime(2026, 4, 3, 4, 5, 6, tzinfo=timezone.utc)


def _rows() -> list[dict]:
    return [
        {
            "day": "Day 1",
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Oslo",
            "title": "Oslo Fjord Cruise",
            "client_description": "Generated activity description",
            "row_id": "row-1",
            "line_number": 1,
            "date": "01/01/2027",
            "start_date": "01/01/2027",
        },
        {
            "day": "Day 2",
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Bergen",
            "title": "Bergen Walk",
            "client_description": "Generated Bergen description",
            "row_id": "row-2",
            "line_number": 2,
            "date": "02/01/2027",
            "start_date": "02/01/2027",
        },
    ]


def _generated_state() -> dict:
    rows = _rows()
    edits = make_output_edit_state(rows, group_rows_by_day(rows))
    edits["output_brand"] = "booknordics_customer"
    edits["trip_title"] = "Generated Norway Trip"
    return {
        "last_generated_raw_text": "RAW SOURCE INPUT",
        "raw_text_input": "RAW SOURCE INPUT",
        "parsed_rows": rows,
        "output_edits": edits,
        "detail_level": "Rich descriptive",
        "day_page_layout": "One day per page",
        "pdf_status": "Not created",
    }


def _named_saved_state() -> dict:
    state = _generated_state()
    project = build_saved_project_from_state(state, itinerary_name="Norway Winter", project_id="project-45", clock=_clock)
    state["active_saved_project"] = saved_project_to_dict(project)
    state["active_saved_project_id"] = "project-45"
    state["itinerary_name"] = "Norway Winter"
    return state


def _apply_current_text_and_image_edits(state: dict) -> None:
    edits = state["output_edits"]
    edits["days"]["Day 1"]["intro"] = "Edited day intro that must survive save and reopen."
    edits["days"]["Day 1"]["intro_manual_override"] = True
    edits["rows"]["row-1"]["title"] = "Edited fjord cruise title"
    edits["rows"]["row-1"]["client_description"] = "Edited activity text that must survive reopen."
    edits["whats_included_pages_html"] = [
        "<section><h3>Manual inclusions</h3><ul><li>Edited private transfers</li></ul></section>"
    ]
    edits["cover_image"] = {"mode": "removed", "removed": True, "path": "images/old-cover.webp"}
    edits["summary_image"] = {"mode": "manual", "path": "images/new-summary.webp", "crop_focus": "top"}
    edits["day_images"] = {
        "Day 1": {"mode": "manual", "path": "images/replaced-oslo.webp", "crop_focus": "bottom"},
        "Day 2": {"mode": "removed", "removed": True, "path": "images/bergen.webp"},
    }
    edits["pictures_added"] = True


def test_current_text_final_and_image_edits_save_and_reopen_from_active_project() -> None:
    state = _named_saved_state()
    baseline_payload = deepcopy(state["active_saved_project"])
    _apply_current_text_and_image_edits(state)

    assert refresh_active_saved_project_current_snapshot(state, clock=_later_clock) is True
    reopened_state: dict = {}
    result = load_saved_project(reopened_state, state["active_saved_project"])

    assert result.ok is True
    assert state["active_saved_project"]["generated_baseline_snapshot"] == baseline_payload["generated_baseline_snapshot"]
    assert reopened_state["output_edits"]["days"]["Day 1"]["intro"] == "Edited day intro that must survive save and reopen."
    assert reopened_state["output_edits"]["rows"]["row-1"]["title"] == "Edited fjord cruise title"
    assert reopened_state["output_edits"]["rows"]["row-1"]["client_description"] == "Edited activity text that must survive reopen."
    assert "Edited private transfers" in reopened_state["output_edits"]["whats_included_pages_html"][0]
    assert reopened_state["output_edits"]["cover_image"]["removed"] is True
    assert reopened_state["output_edits"]["summary_image"]["path"] == "images/new-summary.webp"
    assert reopened_state["output_edits"]["summary_image"]["crop_focus"] == "top"
    assert reopened_state["output_edits"]["day_images"]["Day 1"]["path"] == "images/replaced-oslo.webp"
    assert reopened_state["output_edits"]["day_images"]["Day 1"]["crop_focus"] == "bottom"
    assert reopened_state["output_edits"]["day_images"]["Day 2"]["removed"] is True
    assert reopened_state["app_stage"] == "pictures"


def test_save_project_file_uses_latest_current_snapshot_without_overwriting_baseline() -> None:
    state = _named_saved_state()
    baseline_payload = deepcopy(state["active_saved_project"])
    _apply_current_text_and_image_edits(state)

    project_file = prepare_saved_project_file_download(state, clock=_later_clock)
    project = saved_project_from_dict(project_file.payload)

    assert project.metadata.project_id == "project-45"
    assert project.metadata.updated_at == "2026-04-02T03:04:05Z"
    assert project.generated_baseline_snapshot.output_edits == baseline_payload["generated_baseline_snapshot"]["output_edits"]
    assert project.current_snapshot.output_edits["rows"]["row-1"]["title"] == "Edited fjord cruise title"
    assert project.image_state.day_images["Day 1"]["crop_focus"] == "bottom"
    assert project.image_state.day_images["Day 2"]["removed"] is True


def test_pdf_boundary_saves_export_state_without_saving_pdf_bytes() -> None:
    state = _named_saved_state()
    _apply_current_text_and_image_edits(state)
    state["preview_signature"] = "sig-current"
    state["pdf_signature"] = "sig-current"
    state["export_pdf_signature"] = "sig-current"
    state["pdf_bytes"] = b"%PDF"
    state["export_pdf_bytes"] = b"%PDF"
    state["pdf_status"] = "Ready"

    assert refresh_active_saved_project_current_snapshot(state, clock=_export_clock) is True
    payload = state["active_saved_project"]
    encoded = str(payload)

    assert payload["export_state"]["pdf_status"] == "Ready"
    assert payload["export_state"]["last_exported_at"] == "2026-04-03T04:05:06Z"
    assert "pdf_bytes" not in encoded
    assert "export_pdf_bytes" not in encoded
    assert payload["current_snapshot"]["output_edits"]["day_images"]["Day 1"]["path"] == "images/replaced-oslo.webp"


def test_browser_recovery_and_autosave_fields_are_not_saved_as_project_state() -> None:
    state = _named_saved_state()
    _apply_current_text_and_image_edits(state)
    state["_persistent_draft_recovery_checked"] = "browser-draft-id"
    state["_last_visual_editor_result"] = {"autosave": True, "payload": {"rows": {"row-1": {"title": "draft only"}}}}
    state["output_edits"]["editor_draft"] = {
        "pages": [],
        "browser_recovery_payload": {"rows": {"row-1": {"title": "draft-only stale text"}}},
    }

    refresh_active_saved_project_current_snapshot(state, clock=_later_clock)
    payload_text = str(state["active_saved_project"])

    assert "_last_visual_editor_result" not in payload_text
    assert "_persistent_draft_recovery_checked" not in payload_text
    assert "browser_recovery_payload" not in payload_text
    assert "draft-only stale text" not in payload_text
    assert state["active_saved_project"]["current_snapshot"]["output_edits"]["rows"]["row-1"]["title"] == "Edited fjord cruise title"


def test_no_active_project_means_temporary_recovery_is_not_promoted_to_saved_project() -> None:
    state = _generated_state()
    _apply_current_text_and_image_edits(state)
    state["_last_visual_editor_result"] = {"autosave": True, "payload": {"rows": {"row-1": {"title": "autosave only"}}}}

    assert refresh_active_saved_project_current_snapshot(state, clock=_later_clock) is False

    assert "active_saved_project" not in state
    assert state["output_edits"]["rows"]["row-1"]["title"] == "Edited fjord cruise title"


def test_update_helper_keeps_previous_last_export_time_until_pdf_ready_again() -> None:
    state = _named_saved_state()
    ready_project = update_saved_project_current_snapshot(
        build_saved_project_from_state(state, itinerary_name="Norway Winter", project_id="project-45", clock=_clock),
        {
            **state,
            "preview_signature": "sig-ready",
            "pdf_signature": "sig-ready",
            "pdf_bytes": b"%PDF",
            "pdf_status": "Ready",
        },
        clock=_later_clock,
    )

    edited_again = update_saved_project_current_snapshot(
        ready_project,
        {**state, "pdf_status": "Needs refresh", "pdf_bytes": None, "pdf_signature": None},
        clock=_export_clock,
    )

    assert ready_project.export_state.last_exported_at == "2026-04-02T03:04:05Z"
    assert edited_again.export_state.pdf_status == "Needs refresh"
    assert edited_again.export_state.last_exported_at == "2026-04-02T03:04:05Z"


def test_manual_visual_editor_save_refreshes_active_saved_project(monkeypatch) -> None:
    import streamlit as st
    import visual_editor_component.editor_workflow as editor_workflow
    from tests.support.streamlit_stub import SessionState

    state = SessionState(_named_saved_state())
    st.session_state = state
    monkeypatch.setattr(
        editor_workflow,
        "build_visual_editor_payload",
        lambda parsed_rows, grouped_days, output_edits: {"meta": {"source_signature": "sig"}, "client_output_warnings": []},
    )
    monkeypatch.setattr(editor_workflow, "_try_apply_server_autosave", lambda *args, **kwargs: False)
    monkeypatch.setattr(editor_workflow, "render_visual_page_editor", lambda *args, **kwargs: {"payload": "manual-save"})
    monkeypatch.setattr(editor_workflow.st, "success", lambda *args, **kwargs: None, raising=False)

    def fake_apply(result, output_edits, mark_dirty=None):
        output_edits["rows"]["row-1"]["title"] = "Manual editor save title"
        st.session_state["_visual_editor_last_result_was_autosave"] = False
        st.session_state["_visual_editor_last_result_changed"] = True
        return True

    monkeypatch.setattr(editor_workflow, "apply_visual_editor_result", fake_apply)

    assert editor_workflow.render_visual_editor(state["parsed_rows"], group_rows_by_day(state["parsed_rows"]), state["output_edits"]) is True

    assert state["active_saved_project"]["current_snapshot"]["output_edits"]["rows"]["row-1"]["title"] == "Manual editor save title"


def test_visual_editor_autosave_does_not_refresh_saved_project(monkeypatch) -> None:
    import streamlit as st
    import visual_editor_component.editor_workflow as editor_workflow
    from tests.support.streamlit_stub import SessionState

    state = SessionState(_named_saved_state())
    st.session_state = state
    baseline_title = state["active_saved_project"]["current_snapshot"]["output_edits"]["rows"]["row-1"]["title"]
    monkeypatch.setattr(
        editor_workflow,
        "build_visual_editor_payload",
        lambda parsed_rows, grouped_days, output_edits: {"meta": {"source_signature": "sig"}, "client_output_warnings": []},
    )
    monkeypatch.setattr(editor_workflow, "_try_apply_server_autosave", lambda *args, **kwargs: False)
    monkeypatch.setattr(editor_workflow, "render_visual_page_editor", lambda *args, **kwargs: {"payload": "autosave"})

    def fake_apply(result, output_edits, mark_dirty=None):
        output_edits["rows"]["row-1"]["title"] = "Autosave draft title"
        st.session_state["_visual_editor_last_result_was_autosave"] = True
        st.session_state["_visual_editor_last_result_changed"] = True
        return True

    monkeypatch.setattr(editor_workflow, "apply_visual_editor_result", fake_apply)

    assert editor_workflow.render_visual_editor(state["parsed_rows"], group_rows_by_day(state["parsed_rows"]), state["output_edits"]) is True

    assert state["output_edits"]["rows"]["row-1"]["title"] == "Autosave draft title"
    assert state["active_saved_project"]["current_snapshot"]["output_edits"]["rows"]["row-1"]["title"] == baseline_title


def test_add_pictures_boundary_refreshes_active_project_image_state() -> None:
    from app_modules.editor_commit import ADD_PICTURES_COMMIT_READY_KEY, ADD_PICTURES_COMMIT_REQUEST_KEY, VISUAL_EDITOR_LAST_APPLIED_COMMIT_KEY
    from app_modules.image_stage_action import enter_picture_stage

    state = _named_saved_state()
    state[ADD_PICTURES_COMMIT_REQUEST_KEY] = "7"
    state[ADD_PICTURES_COMMIT_READY_KEY] = True
    state[VISUAL_EDITOR_LAST_APPLIED_COMMIT_KEY] = "7"

    def fake_select(grouped_days, output_edits):
        output_edits.setdefault("day_images", {})["Day 1"] = {
            "mode": "manual",
            "path": "images/add-pictures-oslo.webp",
            "crop_focus": "left",
        }
        return {"Day 1": {"path": "images/add-pictures-oslo.webp"}}

    result = enter_picture_stage(
        state,
        status_func=lambda: {"total_image_count": 1},
        connect_func=lambda: {"total_image_count": 1},
        select_images_func=fake_select,
        audit_images_func=lambda grouped_days, matches, output_edits: [],
        rebuild_preview_func=lambda **kwargs: True,
    )

    assert result.ok is True
    assert state["active_saved_project"]["image_state"]["day_images"]["Day 1"]["path"] == "images/add-pictures-oslo.webp"
    assert state["active_saved_project"]["image_state"]["day_images"]["Day 1"]["crop_focus"] == "left"


def test_create_pdf_stage_boundary_refreshes_active_project_before_export() -> None:
    from app_modules.export_stage_action import enter_export_stage

    state = _named_saved_state()
    state["output_edits"]["day_images"] = {"Day 1": {"mode": "manual", "path": "images/pdf-boundary.webp", "crop_focus": "right"}}
    state["output_edits"]["pictures_added"] = True

    result = enter_export_stage(state, auto_create_pdf=True)

    assert result.ok is True
    assert state["app_stage"] == "export"
    assert state["_pdf_auto_create_requested"] is True
    assert state["active_saved_project"]["current_snapshot"]["output_edits"]["day_images"]["Day 1"]["path"] == "images/pdf-boundary.webp"
    assert state["active_saved_project"]["current_snapshot"]["output_edits"]["day_images"]["Day 1"]["crop_focus"] == "right"

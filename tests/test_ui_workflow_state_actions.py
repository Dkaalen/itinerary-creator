from __future__ import annotations

from types import SimpleNamespace

from app_modules.editor_commit import (
    ADD_PICTURES_COMMIT_READY_KEY,
    ADD_PICTURES_COMMIT_REQUEST_KEY,
    VISUAL_EDITOR_LAST_APPLIED_COMMIT_KEY,
)
from app_modules.workflow_actions import enter_export_stage, enter_picture_stage, retry_image_bank_connection
from app_modules.workflow_state import (
    clear_pdf_artifacts,
    ensure_workflow_defaults,
    image_grouped_days_from_state,
    reset_workflow_state,
    session_stage_from_state,
    set_workflow_stage,
)


READY_BANK = {"full_bank_found": True, "missing_full_bank": False, "destination_image_count": 4}
MISSING_BANK = {"full_bank_found": False, "missing_full_bank": True, "blocking_message": "Missing bank"}


def _mark_add_pictures_apply_changes_ready(state, nonce="apply-1"):
    state[ADD_PICTURES_COMMIT_REQUEST_KEY] = nonce
    state[ADD_PICTURES_COMMIT_READY_KEY] = True
    state[VISUAL_EDITOR_LAST_APPLIED_COMMIT_KEY] = nonce


def test_workflow_state_normalizes_stage_and_blocks_picture_stage_without_pictures():
    state = {}
    ensure_workflow_defaults(state)

    assert state["app_stage"] == "input"
    assert session_stage_from_state(state) == "input"

    state["parsed_rows"] = [{"day": "Day 1", "city": "Oslo"}]
    set_workflow_stage(state, "export")
    assert session_stage_from_state(state) == "edit"

    state["output_edits"] = {"pictures_added": True}
    assert session_stage_from_state(state) == "export"

    assert set_workflow_stage(state, "unknown") == "input"


def test_clear_pdf_artifacts_clears_all_durable_pdf_state():
    state = {
        "pdf_bytes": b"pdf",
        "export_pdf_bytes": b"pdf",
        "pdf_signature": "sig",
        "export_pdf_signature": "sig",
        "pdf_status": "Ready",
    }

    clear_pdf_artifacts(state, status="Needs refresh")

    assert state["pdf_bytes"] is None
    assert state["export_pdf_bytes"] is None
    assert state["pdf_signature"] is None
    assert state["export_pdf_signature"] is None
    assert state["pdf_status"] == "Needs refresh"


def test_reset_workflow_state_removes_gateway_and_returns_to_input():
    state = {"parsed_rows": [1], "image_bank_gateway": {"ready": False}, "raw_text_input": "abc"}

    reset_workflow_state(state, clear_raw_text=True)

    assert state["parsed_rows"] == []
    assert state["app_stage"] == "input"
    assert state["raw_text_input"] == ""
    assert "image_bank_gateway" not in state


def test_image_grouped_days_excludes_optional_rows_when_possible():
    state = {
        "parsed_rows": [
            {"day": "Day 1", "city": "Oslo", "title": "Included"},
            {"day": "Day 1", "city": "Oslo", "title": "Optional", "is_optional": True},
        ]
    }

    grouped = image_grouped_days_from_state(state)

    assert [row["title"] for row in grouped["Day 1"]] == ["Included"]


def test_enter_picture_stage_requires_applied_preview_changes_before_image_selection():
    state = {
        "app_stage": "edit",
        "parsed_rows": [{"day": "Day 1", "city": "Oslo"}],
        "output_edits": {"pictures_added": False},
    }
    calls = {"select": 0, "connect": 0, "rebuild": 0}

    result = enter_picture_stage(
        state,
        status_func=lambda: READY_BANK,
        connect_func=lambda: calls.__setitem__("connect", calls["connect"] + 1) or READY_BANK,
        select_images_func=lambda grouped, edits: calls.__setitem__("select", calls["select"] + 1) or {},
        audit_images_func=lambda grouped, matches, edits: (),
        rebuild_preview_func=lambda **kwargs: calls.__setitem__("rebuild", calls["rebuild"] + 1) or True,
    )

    assert result.ok is False
    assert result.payload == {"requires_apply_changes": True}
    assert result.message == "Apply changes before adding pictures."
    assert state["app_stage"] == "edit"
    assert state["output_edits"]["pictures_added"] is False
    assert calls == {"select": 0, "connect": 0, "rebuild": 0}


def test_enter_picture_stage_blocks_missing_bank_and_clears_stale_pdf():
    state = {
        "app_stage": "edit",
        "parsed_rows": [{"day": "Day 1", "city": "Oslo"}],
        "output_edits": {"pictures_added": True},
        "pdf_bytes": b"old",
        "export_pdf_bytes": b"old",
        "pdf_signature": "old",
        "export_pdf_signature": "old",
    }
    calls = {"rebuild": 0}
    _mark_add_pictures_apply_changes_ready(state)

    result = enter_picture_stage(
        state,
        status_func=lambda: MISSING_BANK,
        connect_func=lambda: MISSING_BANK,
        select_images_func=lambda grouped, edits: {},
        audit_images_func=lambda grouped, matches, edits: (),
        rebuild_preview_func=lambda **kwargs: calls.__setitem__("rebuild", calls["rebuild"] + 1) or True,
    )

    assert result.ok is False
    assert state["app_stage"] == "edit"
    assert state["output_edits"]["pictures_added"] is False
    assert state["output_edits"]["allow_default_final_images"] is False
    assert state["pdf_bytes"] is None
    assert state["export_pdf_bytes"] is None
    assert state["pdf_status"] == "Image bank missing"
    assert calls["rebuild"] == 0


def test_enter_picture_stage_sets_review_state_and_marks_pdf_dirty():
    state = {
        "app_stage": "edit",
        "parsed_rows": [{"day": "Day 1", "city": "Oslo", "title": "Walk"}],
        "output_edits": {},
        "pdf_bytes": b"old",
        "export_pdf_bytes": b"old",
    }
    rebuild_calls = []
    _mark_add_pictures_apply_changes_ready(state)

    result = enter_picture_stage(
        state,
        status_func=lambda: READY_BANK,
        connect_func=lambda: READY_BANK,
        select_images_func=lambda grouped, edits: {"Day 1": "oslo.webp"},
        audit_images_func=lambda grouped, matches, edits: [SimpleNamespace(severity="warning")],
        rebuild_preview_func=lambda **kwargs: rebuild_calls.append(kwargs) or True,
    )

    assert result.ok is True
    assert state["app_stage"] == "pictures"
    assert state["output_edits"]["pictures_added"] is True
    assert state["image_review_warning_count"] == 0
    assert state["pdf_bytes"] is None
    assert state["export_pdf_bytes"] is None
    assert rebuild_calls == [{"mark_pdf_dirty": True, "force": True, "save_html": True}]
    assert "image_bank_gateway" not in state
    assert state.get(ADD_PICTURES_COMMIT_REQUEST_KEY) is None
    assert state.get(ADD_PICTURES_COMMIT_READY_KEY) is False


def test_enter_picture_stage_uses_committed_day_edits_for_image_matching():
    state = {
        "app_stage": "edit",
        "parsed_rows": [{"day": "Day 1", "city": "Oslo", "title": "Walk"}],
        "output_edits": {"days": {"Day 1": {"city": "Bergen", "title": "Edited Bergen Day"}}},
    }
    _mark_add_pictures_apply_changes_ready(state)
    captured = {}

    result = enter_picture_stage(
        state,
        status_func=lambda: READY_BANK,
        connect_func=lambda: READY_BANK,
        select_images_func=lambda grouped, edits: (captured.setdefault("grouped", grouped), {"Day 1": "bergen.webp"})[1],
        audit_images_func=lambda grouped, matches, edits: (),
        rebuild_preview_func=lambda **kwargs: True,
    )

    assert result.ok is True
    overview = captured["grouped"]["Day 1"][0]
    assert overview["effective_type"] == "Day Overview"
    assert overview["city"] == "Bergen"
    assert overview["title"] == "Edited Bergen Day"


def test_enter_picture_stage_treats_day_image_matches_as_derived_metadata():
    state = {
        "app_stage": "edit",
        "parsed_rows": [{"day": "Day 1", "city": "Oslo", "title": "Walk"}],
        "output_edits": {
            "day_images": {"Day 1": {"mode": "manual", "path": "manual-oslo.webp"}},
            "day_image_matches": {"Day 1": {"path": "stale-auto.webp"}},
        },
    }
    _mark_add_pictures_apply_changes_ready(state)
    captured = {}

    result = enter_picture_stage(
        state,
        status_func=lambda: READY_BANK,
        connect_func=lambda: READY_BANK,
        select_images_func=lambda grouped, edits: (captured.setdefault("edits", edits), {"Day 1": {"path": edits["day_images"]["Day 1"]["path"]}})[1],
        audit_images_func=lambda grouped, matches, edits: (),
        rebuild_preview_func=lambda **kwargs: True,
    )

    assert result.ok is True
    assert captured["edits"]["day_images"]["Day 1"]["path"] == "manual-oslo.webp"
    assert state["output_edits"]["day_images"]["Day 1"]["path"] == "manual-oslo.webp"
    assert state["output_edits"]["day_image_matches"]["Day 1"]["path"] == "manual-oslo.webp"


def test_retry_image_bank_connection_keeps_gateway_result_in_state():
    state = {"app_stage": "edit"}

    result = retry_image_bank_connection(state, lambda: MISSING_BANK, lambda: READY_BANK)

    assert result.ok is True
    assert state["image_bank_gateway"]["ready"] is True
    assert state["image_bank_status"] == READY_BANK


def test_enter_export_stage_requests_commit_and_sets_export_stage():
    state = {"app_stage": "pictures"}
    calls = {"commit": 0}

    result = enter_export_stage(state, request_pdf_commit_func=lambda: calls.__setitem__("commit", calls["commit"] + 1))

    assert result.ok is True
    assert state["app_stage"] == "export"
    assert calls["commit"] == 1


def test_load_project_uses_workflow_action_state_rules():
    from app_modules.workflow_actions import load_project

    raw_text = """
Day 1	Hotel	01/01/2027	02/01/2027					Oslo	3 Star, Test Hotel, 1xNight, 1xStandard Room, Incl Breakfast
"""
    state = {
        "app_stage": "input",
        "pdf_bytes": b"old",
        "export_pdf_bytes": b"old",
        "day_page_layout": "single",
    }

    result = load_project(state, raw_text, {"pictures_added": True, "detail_level": "Standard client itinerary"})

    assert result.ok is True
    assert state["app_stage"] == "pictures"
    assert state["detail_level"] == "Rich descriptive"
    assert state["output_edits"]["detail_level"] == "Rich descriptive"
    assert state["output_edits"]["pictures_added"] is True
    assert state["raw_text_input"] == raw_text
    assert state["itinerary_html"]
    assert state["html_path"]
    assert state["pdf_bytes"] is None
    assert state["export_pdf_bytes"] is None


def test_project_io_delegates_project_loading_to_workflow_actions():
    from pathlib import Path

    source = Path("app_modules/project_io.py").read_text(encoding="utf-8")
    action_source = Path("app_modules/workflow_actions.py").read_text(encoding="utf-8")

    assert "from app_modules.workflow_actions import load_project" in source
    assert "result = load_project(st.session_state" in source
    assert "def load_project(" in action_source
    assert "set_workflow_stage(state, \"pictures\" if pictures_are_added" in action_source

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from tests.support.static_contracts import read_contract_text

from app_modules.render_context_cache import get_cached_render_context
from app_modules.saved_project_builder import build_saved_project_from_state
from app_modules.saved_project_load_action import load_saved_project
from app_modules.saved_project_serialization import saved_project_to_dict
from app_modules.saved_project_update import update_saved_project_current_snapshot
from app_modules.workflow_actions import load_saved_project as workflow_load_saved_project
from itinerary_generation.common import group_rows_by_day
from ui.output_edits import make_output_edit_state
from ui.render_cache import make_render_signature


def _clock() -> datetime:
    return datetime(2026, 2, 3, 4, 5, 6, tzinfo=timezone.utc)


def _later_clock() -> datetime:
    return datetime(2026, 2, 4, 5, 6, 7, tzinfo=timezone.utc)


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
    edits["output_brand"] = "agent"
    return {
        "last_generated_raw_text": "RAW SOURCE THAT MUST NOT BE REPARSED",
        "raw_text_input": "stale raw input",
        "parsed_rows": rows,
        "output_edits": edits,
        "detail_level": "Rich descriptive",
        "day_page_layout": "One day per page",
        "pdf_status": "Needs refresh",
    }


def _edited_state() -> dict:
    state = deepcopy(_generated_state())
    edits = state["output_edits"]
    edits["days"]["Day 1"]["intro"] = "Manual saved intro from reopened project."
    edits["days"]["Day 1"]["intro_manual_override"] = True
    edits["rows"]["row-1"]["title"] = "Edited saved cruise title"
    edits["rows"]["row-1"]["client_description"] = "Edited saved row description."
    edits["whats_included_pages_html"] = ["<section><h3>Manual inclusions</h3><ul><li>Saved private cruise</li></ul></section>"]
    edits["whats_included_text"] = ""
    edits["cover_image"] = {"mode": "manual", "path": "images/cover.webp", "crop_focus": "top"}
    edits["summary_image"] = {"mode": "manual", "path": "images/summary.webp", "crop_focus": "center"}
    edits["day_images"] = {"Day 1": {"mode": "manual", "path": "images/oslo.webp", "crop_focus": "bottom"}}
    edits["pictures_added"] = True
    return state


def _saved_project_with_current_edits():
    project = build_saved_project_from_state(_generated_state(), itinerary_name="Saved Oslo", project_id="project-42", clock=_clock)
    return update_saved_project_current_snapshot(project, _edited_state(), clock=_later_clock)


def test_saved_project_reopen_uses_current_snapshot_without_reparse_or_regeneration(monkeypatch) -> None:
    import app_modules.project_load_action as legacy_project_loader

    def fail_parse(*args, **kwargs):  # pragma: no cover - only runs on regression
        raise AssertionError("Saved-project reopen must not parse raw source input.")

    monkeypatch.setattr(legacy_project_loader, "parse_and_normalize_itinerary", fail_parse)
    state = {"app_stage": "input", "pdf_bytes": b"old", "export_pdf_bytes": b"old"}

    result = load_saved_project(state, _saved_project_with_current_edits())

    assert result.ok is True
    assert state["app_stage"] == "pictures"
    assert state["parsed_rows"] == _rows()
    assert state["raw_text_input"] == "RAW SOURCE THAT MUST NOT BE REPARSED"
    assert state["output_edits"]["days"]["Day 1"]["intro"] == "Manual saved intro from reopened project."
    assert state["output_edits"]["days"]["Day 1"]["intro_manual_override"] is True
    assert state["output_edits"]["rows"]["row-1"]["title"] == "Edited saved cruise title"
    assert state["output_edits"]["rows"]["row-1"]["client_description"] == "Edited saved row description."
    assert state["pdf_bytes"] is None
    assert state["export_pdf_bytes"] is None
    assert state["pdf_status"] == "Not created"


def test_saved_project_reopen_preserves_final_sections_and_image_state() -> None:
    state = {"day_image_matches": {"Day 1": "stale"}, "image_bank_status": {"ready": False}}

    result = workflow_load_saved_project(state, saved_project_to_dict(_saved_project_with_current_edits()))

    assert result.ok is True
    assert "day_image_matches" not in state
    assert "image_bank_status" not in state
    assert state["output_edits"]["whats_included_pages_html"] == [
        "<section><h3>Manual inclusions</h3><ul><li>Saved private cruise</li></ul></section>"
    ]
    assert state["output_edits"]["cover_image"] == {"mode": "manual", "path": "images/cover.webp", "crop_focus": "top"}
    assert state["output_edits"]["summary_image"] == {"mode": "manual", "path": "images/summary.webp", "crop_focus": "center"}
    assert state["output_edits"]["day_images"] == {
        "Day 1": {"mode": "manual", "path": "images/oslo.webp", "crop_focus": "bottom"}
    }
    assert state["output_edits"]["pictures_added"] is True


def test_saved_project_reopen_rebuilds_preview_and_pdf_render_context_from_saved_state() -> None:
    state = {}

    result = load_saved_project(state, _saved_project_with_current_edits())

    assert result.ok is True
    expected_signature = make_render_signature(state["parsed_rows"], state["output_edits"])
    assert state["preview_signature"] == expected_signature
    assert state["itinerary_html"]
    assert Path(state["html_path"]).exists()
    cached_context = get_cached_render_context(state, signature=expected_signature)
    assert cached_context is not None
    assert cached_context.render_document.days[0].intro == "Manual saved intro from reopened project."
    assert cached_context.render_document.days[0].blocks[0].title == "Edited saved cruise title"
    assert "Saved private cruise" in cached_context.render_document.final_sections[0].pages[0].content_html


def test_saved_project_update_keeps_baseline_distinct_from_current_snapshot() -> None:
    project = build_saved_project_from_state(_generated_state(), itinerary_name="Saved Oslo", project_id="project-42", clock=_clock)
    updated = update_saved_project_current_snapshot(project, _edited_state(), clock=_later_clock)

    assert updated.metadata.created_at == "2026-02-03T04:05:06Z"
    assert updated.metadata.updated_at == "2026-02-04T05:06:07Z"
    assert updated.generated_baseline_snapshot.output_edits["rows"]["row-1"]["title"] != "Edited saved cruise title"
    assert updated.current_snapshot.output_edits["rows"]["row-1"]["title"] == "Edited saved cruise title"
    assert updated.image_state.day_images["Day 1"]["path"] == "images/oslo.webp"


def test_saved_project_reopen_source_does_not_import_parse_or_text_refresh() -> None:
    source = read_contract_text("app_modules/saved_project_load_action.py")

    assert "parse_and_normalize_itinerary" not in source
    assert "make_output_edit_state" not in source
    assert "refresh_generated_text_for_detail_level" not in source

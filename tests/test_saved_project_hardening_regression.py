from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from app_modules.export_identity import export_signature_for_state
from app_modules.saved_project_builder import build_saved_project_from_state
from app_modules.saved_project_file_action import prepare_saved_project_file_download
from app_modules.saved_project_load_action import load_saved_project
from app_modules.saved_project_serialization import saved_project_from_dict, saved_project_from_json, saved_project_to_dict
from app_modules.saved_project_validation import SavedProjectError, validate_saved_project_payload
from itinerary_generation.common import group_rows_by_day
from tests.support.streamlit_stub import install_streamlit_stub
from ui.output_edits import make_output_edit_state
from ui.render_cache import make_render_signature


def _clock() -> datetime:
    return datetime(2026, 6, 1, 8, 9, 10, tzinfo=timezone.utc)


def _later_clock() -> datetime:
    return datetime(2026, 6, 2, 9, 10, 11, tzinfo=timezone.utc)


def _export_clock() -> datetime:
    return datetime(2026, 6, 3, 10, 11, 12, tzinfo=timezone.utc)


def _rows() -> list[dict]:
    return [
        {
            "day": "Day 1",
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Oslo",
            "title": "Oslo Fjord Cruise",
            "client_description": "Generated Oslo description",
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
    edits["output_brand"] = "agent"
    edits["trip_title"] = "Norway Saved Project"
    return {
        "last_generated_raw_text": "RAW SOURCE INPUT THAT MUST NOT BE REGENERATED",
        "raw_text_input": "RAW SOURCE INPUT THAT MUST NOT BE REGENERATED",
        "parsed_rows": rows,
        "output_edits": edits,
        "detail_level": "Rich descriptive",
        "day_page_layout": "One day per page",
        "pdf_status": "Not created",
    }


def _apply_edits(state: dict) -> None:
    edits = state["output_edits"]
    edits["days"]["Day 1"]["intro"] = "Saved edited Oslo intro."
    edits["days"]["Day 1"]["intro_manual_override"] = True
    edits["rows"]["row-1"]["title"] = "Edited Oslo fjord title"
    edits["rows"]["row-1"]["client_description"] = "Edited Oslo description for the customer."
    edits["whats_included_pages_html"] = [
        "<section><h3>Included Services</h3><ul><li>Edited private transfers</li></ul></section>"
    ]
    edits["cover_image"] = {"mode": "manual", "path": "images/cover.webp", "crop_focus": "top"}
    edits["summary_image"] = {"mode": "manual", "path": "images/summary.webp", "crop_focus": "center"}
    edits["day_images"] = {
        "Day 1": {"mode": "manual", "path": "images/oslo-replaced.webp", "crop_focus": "bottom"},
        "Day 2": {"mode": "removed", "removed": True, "path": "images/bergen-old.webp"},
    }
    edits["pictures_added"] = True


def _saved_project_with_edits():
    state = _generated_state()
    project = build_saved_project_from_state(state, itinerary_name="Norway Saved Project", project_id="project-47", clock=_clock)
    state["active_saved_project"] = saved_project_to_dict(project)
    state["active_saved_project_id"] = project.metadata.project_id
    _apply_edits(state)
    return saved_project_from_dict(prepare_saved_project_file_download(state, clock=_later_clock).payload)


def test_generate_save_reopen_preview_is_stable_and_does_not_reparse(monkeypatch) -> None:
    import app_modules.project_load_action as legacy_project_loader

    def fail_parse(*args, **kwargs):  # pragma: no cover - regression guard
        raise AssertionError("Saved-project reopen must not parse or regenerate source input.")

    monkeypatch.setattr(legacy_project_loader, "parse_and_normalize_itinerary", fail_parse)
    state = _generated_state()
    _apply_edits(state)

    project_file = prepare_saved_project_file_download(state, itinerary_name="Norway Saved Project", clock=_clock)
    reopened_state: dict = {}
    result = load_saved_project(reopened_state, json.loads(project_file.data.decode("utf-8")))

    assert result.ok is True
    assert reopened_state["raw_text_input"] == "RAW SOURCE INPUT THAT MUST NOT BE REGENERATED"
    assert reopened_state["output_edits"]["rows"]["row-1"]["title"] == "Edited Oslo fjord title"
    assert "Edited private transfers" in reopened_state["output_edits"]["whats_included_pages_html"][0]
    assert reopened_state["output_edits"]["day_images"]["Day 1"]["crop_focus"] == "bottom"
    assert reopened_state["output_edits"]["day_images"]["Day 2"]["removed"] is True
    assert reopened_state["preview_signature"] == make_render_signature(reopened_state["parsed_rows"], reopened_state["output_edits"])
    assert "Edited Oslo fjord title" in reopened_state["itinerary_html"]


def test_saved_project_payload_hardening_rejects_hash_mismatch_temp_fields_and_size() -> None:
    project = _saved_project_with_edits()
    payload = saved_project_to_dict(project)

    corrupted = deepcopy(payload)
    corrupted["source"]["source_input"] = "changed source without matching hash"
    with pytest.raises(SavedProjectError, match="source hash"):
        validate_saved_project_payload(corrupted)

    bloated = deepcopy(payload)
    bloated["current_snapshot"]["output_edits"]["day_images"]["Day 1"]["preview_data_uri"] = "data:image/png;base64,AAAA"
    with pytest.raises(SavedProjectError, match="temporary or preview-only"):
        validate_saved_project_payload(bloated)

    with pytest.raises(SavedProjectError, match="too large"):
        validate_saved_project_payload(payload, max_bytes=200)


def test_corrupt_and_wrong_schema_project_files_fail_safely() -> None:
    with pytest.raises(json.JSONDecodeError):
        saved_project_from_json("{not json")

    wrong_schema = saved_project_to_dict(_saved_project_with_edits())
    wrong_schema["saved_schema_version"] = 999
    with pytest.raises(SavedProjectError, match="Unsupported saved project schema version"):
        saved_project_from_dict(wrong_schema)

    missing_snapshot_id = saved_project_to_dict(_saved_project_with_edits())
    missing_snapshot_id["current_snapshot"]["snapshot_id"] = ""
    with pytest.raises(SavedProjectError, match="snapshot_id"):
        saved_project_from_dict(missing_snapshot_id)


def test_reopen_then_create_pdf_uses_reopened_state(monkeypatch, tmp_path) -> None:
    st = install_streamlit_stub(force=True)
    from app_modules import export_actions, export_pdf_artifacts, export_render_context, project_io

    monkeypatch.setattr(export_actions, "st", st)
    monkeypatch.setattr(export_pdf_artifacts, "st", st)
    monkeypatch.setattr(export_render_context, "st", st)
    monkeypatch.setattr(project_io, "st", st)
    st.session_state.clear()
    load_result = load_saved_project(st.session_state, saved_project_to_dict(_saved_project_with_edits()))
    assert load_result.ok is True

    captured: dict = {}

    monkeypatch.setattr(export_actions, "validate_for_generation", lambda _rows: SimpleNamespace(is_blocked=False))
    monkeypatch.setattr(export_actions, "_preview_contract_blocks_pdf", lambda _html, _expected_day_count: False)
    monkeypatch.setattr(export_actions, "prepare_pdf_image_contract", lambda: (True, {"full_bank_found": True}, {"Day 1": {"path": "images/oslo-replaced.webp"}, "Day 2": None}, []))
    monkeypatch.setattr(export_actions, "_client_safety_blocks_pdf", lambda *_args, **_kwargs: False)

    def fake_save_pdf_file(html_path, *, render_document, day_images, day_image_crop_focus, output_edits, **kwargs):
        pdf_path = tmp_path / "reopened-itinerary.pdf"
        pdf_path.write_bytes(b"%PDF-reopened-state")
        captured["html_path"] = str(html_path)
        captured["titles"] = [block.title for day in render_document.days for block in day.blocks]
        captured["final_html"] = render_document.final_sections[0].pages[0].content_html
        captured["day_images"] = day_images
        captured["crop_focus"] = day_image_crop_focus
        captured["output_edits"] = output_edits
        return str(pdf_path)

    monkeypatch.setattr(export_actions, "save_pdf_file", fake_save_pdf_file)

    assert export_actions.create_pdf_from_current_preview() is True

    assert st.session_state["pdf_bytes"] == b"%PDF-reopened-state"
    assert st.session_state["pdf_signature"] == export_signature_for_state(st.session_state)
    assert st.session_state["export_pdf_signature"] == export_signature_for_state(st.session_state)
    assert "Edited Oslo fjord title" in captured["titles"]
    assert "Edited private transfers" in captured["final_html"]
    assert captured["day_images"]["Day 1"]["path"] == "images/oslo-replaced.webp"
    assert captured["day_images"]["Day 2"] is None
    assert captured["crop_focus"]["Day 1"] == "bottom"
    assert captured["output_edits"]["day_images"]["Day 2"]["removed"] is True
    assert Path(captured["html_path"]).exists()


def test_saved_project_hardening_has_no_duplicate_renderer_or_session_dump_sources() -> None:
    saved_modules = [path for path in Path("app_modules").glob("saved_project*.py")]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in saved_modules)

    assert "st.session_state" not in combined
    assert "build_itinerary_html_from_context" not in Path("app_modules/saved_project_builder.py").read_text(encoding="utf-8")
    assert "save_pdf_file" not in combined
    assert "parse_and_normalize_itinerary" not in combined
    assert "preview_html" in Path("app_modules/saved_project_constants.py").read_text(encoding="utf-8")

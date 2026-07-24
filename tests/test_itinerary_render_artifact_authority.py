from __future__ import annotations

from pathlib import Path

from app_modules.export_render_context import pdf_render_context_for_state
from app_modules.itinerary_render_artifact import (
    build_and_persist_itinerary_render_artifact,
    build_itinerary_render_artifact,
)
from app_modules.render_context_cache import get_cached_render_context
from itinerary_generation.common import group_rows_by_day
from ui.output_edits import make_output_edit_state
from ui.render_cache import make_render_signature


ROOT = Path(__file__).resolve().parents[1]


def _rows() -> list[dict]:
    return [
        {
            "day": "Day 1",
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Oslo",
            "title": "Original title",
            "client_description": "Original description.",
            "row_id": "row-1",
            "line_number": 1,
            "date": "01/01/2027",
            "start_date": "01/01/2027",
        }
    ]


def _edits(rows: list[dict]) -> dict:
    edits = make_output_edit_state(rows, group_rows_by_day(rows))
    edits["rows"]["row-1"]["title"] = "Edited title"
    return edits


def test_artifact_owns_edits_grouping_context_html_signature_and_warnings() -> None:
    rows = _rows()
    edits = _edits(rows)

    artifact = build_itinerary_render_artifact(rows, edits)

    assert artifact.edited_rows[0]["title"] == "Edited title"
    assert artifact.grouped_days == group_rows_by_day(artifact.edited_rows)
    assert artifact.render_context.parsed_rows == artifact.edited_rows
    assert artifact.render_context.grouped_days == artifact.grouped_days
    assert "Edited title" in artifact.html
    assert artifact.signature == make_render_signature(rows, edits)
    assert artifact.overflow_warnings == []


def test_persisted_artifact_is_shared_by_preview_cache_and_pdf_fallback() -> None:
    rows = _rows()
    edits = _edits(rows)
    state: dict = {"parsed_rows": rows, "output_edits": edits}

    artifact = build_and_persist_itinerary_render_artifact(
        state,
        parsed_rows=rows,
        output_edits=edits,
        save_html=False,
    )

    assert state["itinerary_html"] == artifact.html
    assert state["preview_signature"] == artifact.signature
    assert get_cached_render_context(state, signature=artifact.signature) is artifact.render_context
    assert pdf_render_context_for_state(state, artifact.signature) is artifact.render_context


def test_pdf_fallback_uses_canonical_builder_without_replacing_visible_preview() -> None:
    rows = _rows()
    edits = _edits(rows)
    signature = make_render_signature(rows, edits)
    state = {
        "parsed_rows": rows,
        "output_edits": edits,
        "itinerary_html": "existing visible preview",
        "preview_signature": signature,
    }

    context = pdf_render_context_for_state(state, signature)

    assert context.render_document.days[0].blocks[0].title == "Edited title"
    assert state["itinerary_html"] == "existing visible preview"
    assert state["preview_signature"] == signature
    assert get_cached_render_context(state, signature=signature) is context


def test_all_workflow_construction_paths_delegate_to_one_artifact_owner() -> None:
    owner = ROOT / "app_modules" / "itinerary_render_artifact.py"
    assert owner.exists()
    assert not (ROOT / "app_modules" / "generation_preview_builder.py").exists()

    owner_source = owner.read_text(encoding="utf-8")
    assert owner_source.count("build_itinerary_render_context(") == 1
    assert owner_source.count("build_itinerary_html_from_context(") == 1
    assert owner_source.count("apply_output_edits(") == 1
    assert owner_source.count("group_rows_by_day(") == 1
    assert owner_source.count("make_render_signature(") == 1

    consumers = (
        "generation_action.py",
        "project_load_action.py",
        "saved_project_restore.py",
        "preview_rebuild.py",
        "export_render_context.py",
    )
    forbidden = (
        "build_itinerary_render_context",
        "build_itinerary_html_from_context",
        "apply_output_edits",
        "store_render_context",
    )
    for filename in consumers:
        source = (ROOT / "app_modules" / filename).read_text(encoding="utf-8")
        assert "build_and_persist_itinerary_render_artifact" in source
        for name in forbidden:
            assert name not in source

from __future__ import annotations

import ast
from pathlib import Path

from app_modules.itinerary_render_context import build_itinerary_render_context
from app_modules.render_final_sections_html import render_final_page_inner_html
from itinerary_generation.common import group_rows_by_day
from itinerary_generation.editable_draft import normalise_editable_draft
from ui.render_blocks import render_blocks_to_html
from visual_editor_component.editor_payload_builder import build_visual_editor_payload


ROOT = Path(__file__).resolve().parents[1]


def _rows() -> list[dict]:
    return [
        {
            "row_id": "row-1",
            "line_number": 1,
            "day": "Day 1",
            "type": "Activity",
            "effective_type": "Activity",
            "source_type": "Activity",
            "city": "Oslo",
            "title": "Oslo Walking Tour",
            "client_description": "Explore central Oslo with a local guide.",
            "start_date": "01/01/2027",
        },
        {
            "row_id": "row-2",
            "line_number": 2,
            "day": "Day 2",
            "type": "Activity",
            "effective_type": "Activity",
            "source_type": "Activity",
            "city": "Bergen",
            "title": "Bergen Food Walk",
            "client_description": "Taste local flavours in historic Bergen.",
            "start_date": "02/01/2027",
        },
    ]


def _section_pages(section):
    return list(section.pages or [])


def test_editor_payload_projects_prepared_render_document_content() -> None:
    rows = _rows()
    grouped = group_rows_by_day(rows)
    context = build_itinerary_render_context(rows, grouped, {"pictures_added": False})

    payload = build_visual_editor_payload(
        rows,
        grouped,
        {"pictures_added": False},
        render_context=context,
    )

    document = context.editor_render_document
    assert payload["meta"]["content_authority"] == "render_document"
    assert payload["cover"]["trip_title"] == document.cover.title
    assert payload["cover"]["destinations_line"] == document.cover.route
    assert payload["summary"]["trip_glance"] == {
        item.label: item.value for item in document.summary.trip_glance
    }

    payload_days = {day["day"]: day for day in payload["days"]}
    for render_day in document.days:
        editor_day = payload_days[render_day.day]
        assert editor_day["title"] == render_day.title
        assert editor_day["intro"] == render_day.intro
        assert editor_day["city"] == render_day.city
        assert editor_day["date"] == render_day.date
        assert editor_day["blocks_html"] == render_blocks_to_html(render_day.blocks)
        assert editor_day["blocks_html_generated_value"] == render_blocks_to_html(render_day.generated_blocks)

    sections = {section.section_id: section for section in document.final_sections}
    included = sections["whats_included"]
    expected_inclusion_pages = [
        render_final_page_inner_html(included, page)
        for page in _section_pages(included)
    ]
    assert [page["html"] for page in payload["final_pages"]["whats_included_pages_html"]] == expected_inclusion_pages


def test_editor_document_keeps_hidden_generated_pages_for_restore() -> None:
    rows = _rows()
    grouped = group_rows_by_day(rows)
    editor_draft = normalise_editable_draft(
        {
            "days": [
                {"day": "Day 1", "title": "Oslo", "blocks_html": "<div>Oslo</div>"},
                {"day": "Day 2", "title": "Bergen", "blocks_html": "<div>Bergen</div>"},
            ],
            "document_pages": [
                {
                    "page_id": "day-day-2",
                    "page_type": "generated_day",
                    "title": "Day 2",
                    "is_hidden": True,
                }
            ],
        }
    )
    output_edits = {"pictures_added": False, "editor_draft": editor_draft}
    context = build_itinerary_render_context(rows, grouped, output_edits)

    assert [day.day for day in context.render_document.days] == ["Day 1"]
    assert [day.day for day in context.editor_render_document.days] == ["Day 1", "Day 2"]

    payload = build_visual_editor_payload(rows, grouped, output_edits, render_context=context)
    assert [day["day"] for day in payload["days"]] == ["Day 1", "Day 2"]
    hidden_page = next(page for page in payload["document_pages"] if page["page_id"] == "day-day-2")
    assert hidden_page["is_hidden"] is True


def test_editor_payload_no_longer_calls_parallel_content_builders(monkeypatch) -> None:
    import visual_editor_component.editor_payload_days as legacy_days
    import visual_editor_component.editor_payload_final_pages as legacy_final
    import visual_editor_component.editor_payload_sections as legacy_sections

    def fail(*_args, **_kwargs):  # pragma: no cover - architecture guard
        raise AssertionError("parallel editor content builder was called")

    monkeypatch.setattr(legacy_days, "build_payload_days", fail)
    monkeypatch.setattr(legacy_final, "build_final_pages_payload", fail)
    monkeypatch.setattr(legacy_sections, "build_cover_payload", fail)
    monkeypatch.setattr(legacy_sections, "build_summary_payload", fail)

    rows = _rows()
    grouped = group_rows_by_day(rows)
    context = build_itinerary_render_context(rows, grouped, {"pictures_added": False})
    payload = build_visual_editor_payload(rows, grouped, {"pictures_added": False}, render_context=context)

    assert payload["days"]
    assert payload["final_pages"]


def test_editor_payload_builder_has_no_independent_day_or_final_generation_calls() -> None:
    source = (ROOT / "visual_editor_component" / "editor_payload_builder.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert "build_itinerary_render_artifact" in calls
    assert "build_day_payloads_from_render_document" in calls
    assert "build_final_pages_payload_from_render_document" in calls
    assert calls.isdisjoint(
        {
            "resolve_day_content",
            "build_day_blocks",
            "build_payload_days",
            "build_itinerary_document",
            "build_final_pages_payload",
        }
    )


def test_prepared_surfaces_share_one_continuity_report_instance() -> None:
    rows = _rows()
    grouped = group_rows_by_day(rows)
    context = build_itinerary_render_context(rows, grouped, {"pictures_added": False})

    report = context.structured_document.continuity_report
    assert report is not None
    assert context.continuity_report is report
    assert context.render_document.continuity_report is report
    assert context.editor_render_document.continuity_report is report

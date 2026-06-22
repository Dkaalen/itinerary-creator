from pathlib import Path

from app_modules.itinerary_html import build_itinerary_html
from app_modules.itinerary_render_context import build_itinerary_render_context
from itinerary_generation.editable_draft import normalise_editable_draft
from itinerary_generation.editor_page_contract import (
    build_editor_document_pages,
    final_section_is_hidden,
    hidden_page_ids,
    manual_pages_from_draft,
    ordered_page_ids,
    page_is_hidden,
    page_order_from_draft,
)


def _frontend_source() -> str:
    frontend = Path("visual_editor_component/frontend")
    parts = []
    for relative in (
        "styles/editor.css",
        "js/state.js",
        "js/render.js",
        "js/serialization.js",
        "js/editor_dirty_state.js",
            "js/editor_text_tools.js",
            "js/editor_document_model.js",
            "js/editor_inspector.js",
            "js/editor_page_actions.js",
            "js/editor_warnings.js",
            "js/commands.js",
        "js/editing.js",
    ):
        parts.append((frontend / relative).read_text(encoding="utf-8"))
    return "\n".join(parts)


def test_page_contract_marks_every_generated_page_as_editable_and_hideable():
    payload = {
        "cover": {"trip_title": "Nordic Escape"},
        "summary": {"trip_glance": {"Start": "Oslo"}},
        "days": [{"day": "Day 1", "title": "Oslo", "blocks_html": "<div>Walk</div>"}],
        "final_pages": {"whats_not_included_html": "<ul><li>Flights</li></ul>"},
    }

    pages = build_editor_document_pages(payload=payload, grouped_days={"Day 1": []})

    assert {page["page_id"] for page in pages} >= {"cover", "summary", "day-day-1", "final-whats-not-included"}
    assert all(page["page_actions"]["hide"] for page in pages)
    assert pages[0]["editable_fields"]["trip_title"] == "Nordic Escape"
    assert next(page for page in pages if page["page_id"] == "day-day-1")["generated_blocks"][0]["editable_fields"]["content_html"]


def test_manual_pages_survive_typed_draft_normalization_and_render_contract():
    draft = normalise_editable_draft(
        {
            "document_pages": [
                {
                    "page_id": "manual-1",
                    "page_type": "manual",
                    "title": "Custom note",
                    "sort_order": 99,
                    "manual_blocks": [
                        {
                            "block_id": "manual-1__main",
                            "block_type": "manual_text",
                            "editable_fields": {"content_html": "<div>Editable custom page</div>"},
                        }
                    ],
                }
            ]
        }
    )
    rows = [{"type": "Activity", "effective_type": "Activity", "day": "Day 1", "city": "Oslo", "title": "Walk"}]

    html = build_itinerary_html(rows, {"Day 1": rows}, {"days": {}, "editor_draft": draft})
    context = build_itinerary_render_context(rows, {"Day 1": rows}, {"days": {}, "editor_draft": draft})

    manual = next(page for page in draft["document_pages"] if page["page_id"] == "manual-1")
    assert manual["page_type"] == "manual"
    assert manual["manual_blocks"][0]["editable_fields"]["content_html"] == "<div>Editable custom page</div>"
    assert "Editable custom page" in html
    assert any(section.section_id == "manual-1" for section in context.render_document.final_sections)


def test_hidden_page_ids_drive_preview_and_pdf_render_contract():
    rows = [
        {"type": "Activity", "effective_type": "Activity", "day": "Day 1", "city": "Oslo", "title": "Generated Walk"},
        {"type": "Activity", "effective_type": "Activity", "day": "Day 2", "city": "Bergen", "title": "Generated Cruise"},
    ]
    grouped = {"Day 1": [rows[0]], "Day 2": [rows[1]]}
    editor_draft = normalise_editable_draft(
        {
            "days": [
                {"day": "Day 1", "title": "Edited Oslo", "blocks_html": "<div>Oslo content</div>"},
                {"day": "Day 2", "title": "Edited Bergen", "blocks_html": "<div>Bergen content</div>"},
            ],
            "final_pages": {"whats_not_included_html": "<ul><li>Flights</li></ul>"},
            "document_pages": [
                {"page_id": "day-day-2", "page_type": "generated_day", "title": "Day 2", "is_hidden": True},
                {"page_id": "final-whats-not-included", "page_type": "final_section", "title": "Excluded", "is_hidden": True},
            ],
        }
    )

    html = build_itinerary_html(rows, grouped, {"days": {}, "editor_draft": editor_draft})
    context = build_itinerary_render_context(rows, grouped, {"days": {}, "editor_draft": editor_draft})

    assert "Oslo content" in html
    assert "Bergen content" not in html
    assert "Flights" not in html
    assert [day.day for day in context.render_document.days] == ["Day 1"]
    assert "day-day-2" in context.render_document.hidden_page_ids
    assert not any(section.section_id == "whats_not_included" for section in context.render_document.final_sections)




def test_page_visibility_order_and_manual_page_helpers_share_contract_logic():
    editor_draft = {
        "document_pages": [
            {"page_id": "summary", "page_type": "summary", "sort_order": 20},
            {"page_id": "cover", "page_type": "cover", "sort_order": 10, "is_hidden": True},
            {"page_id": "final-whats-not-included", "page_type": "final_section", "sort_order": 30, "is_hidden": True},
            {
                "page_id": "manual-1",
                "page_type": "manual",
                "title": "Client note",
                "sort_order": 40,
                "manual_blocks": [
                    {"editable_fields": {"content_html": "<p>First</p>"}},
                    {"editable_fields": {"content_html": "<p>Second</p>"}},
                ],
            },
            {
                "page_id": "manual-hidden",
                "page_type": "manual",
                "title": "Hidden note",
                "sort_order": 50,
                "is_hidden": True,
                "manual_blocks": [{"editable_fields": {"content_html": "<p>Hidden</p>"}}],
            },
        ]
    }

    hidden = hidden_page_ids(editor_draft["document_pages"])

    assert page_is_hidden(hidden, "cover")
    assert final_section_is_hidden(hidden, "whats_not_included")
    assert page_order_from_draft(editor_draft) == ["cover", "summary", "final-whats-not-included", "manual-1", "manual-hidden"]
    assert ordered_page_ids(["cover", "summary", "day-day-1"], ["summary", "missing", "cover"]) == ["summary", "cover", "day-day-1"]
    assert manual_pages_from_draft(editor_draft, hidden) == [
        {
            "page_id": "manual-1",
            "title": "Client note",
            "content_html": "<p>First</p><p>Second</p>",
            "sort_order": 40,
        }
    ]


def test_frontend_exposes_document_outline_and_page_actions():
    source = _frontend_source()

    assert "renderDocumentOutline" in source
    assert "Add blank page" in source
    assert "Delete page" in source
    assert "restoreDocumentPage" in source
    assert "addManualPage" in source
    assert "duplicateManualPage" in source
    assert "data-doc-page-action" in source
    assert "document_pages.${realIndex}.manual_blocks" in source
    assert "editor-workspace" in source

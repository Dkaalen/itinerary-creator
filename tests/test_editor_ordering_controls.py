from pathlib import Path

from app_modules.itinerary_render_context import build_itinerary_render_context
from itinerary_generation.editor_page_contract import build_editor_document_pages
from tests.support.frontend_assets import frontend_source


def _frontend_source() -> str:
    return frontend_source()


def test_page_headers_expose_page_ordering_controls():
    source = _frontend_source()
    render_js = Path("visual_editor_component/frontend/js/render.js").read_text(encoding="utf-8")

    assert "moveDocumentPage" in source
    assert "moveDocumentPageToIndex" in source
    assert "renumberDocumentPageOrders" in source
    assert "data-outline-row-page-id" in source
    assert 'data-doc-page-action="move-up"' in source
    assert 'data-doc-page-action="move-down"' in source
    assert "Page order updated" in source
    assert "outline-drag-handle" not in render_js
    assert "data-page-drag-index" not in render_js


def test_manual_blocks_expose_drag_style_ordering_controls():
    source = _frontend_source()

    assert "moveManualBlockToIndex" in source
    assert "data-manual-block-page-id" in source
    assert "data-manual-block-index" in source
    assert "manual-block-drag-handle" in source
    assert "Manual block order updated" in source
    assert "drag-over" in source


def test_generated_pages_are_marked_as_movable_in_page_contract():
    pages = build_editor_document_pages(
        payload={
            "cover": {"trip_title": "Nordic Trip"},
            "summary": {"trip_glance": {}},
            "days": [{"day": "Day 1", "title": "Oslo", "blocks_html": ""}],
            "final_pages": {"important_travel_notes_text": "Bring passport"},
        },
        grouped_days={"Day 1": [{"row_id": "r1", "type": "Activity"}]},
    )

    movable = {page["page_id"]: page["page_actions"].get("move") for page in pages}
    assert movable["cover"] is True
    assert movable["summary"] is True
    assert movable["day-day-1"] is True
    assert movable["final-important-travel-notes"] is True


def test_render_document_uses_canonical_generated_page_order_for_pdf_export():
    rows = [
        {"type": "Activity", "effective_type": "Activity", "day": "Day 1", "city": "Oslo", "title": "Walk"},
        {"type": "Activity", "effective_type": "Activity", "day": "Day 2", "city": "Oslo", "title": "Museum"},
    ]
    editor_draft = {
        "document_pages": [
            {"page_id": "day-day-2", "page_type": "generated_day", "title": "Day 2", "sort_order": 1},
            {"page_id": "cover", "page_type": "cover", "title": "Cover", "sort_order": 2},
            {"page_id": "day-day-1", "page_type": "generated_day", "title": "Day 1", "sort_order": 3},
            {"page_id": "summary", "page_type": "summary", "title": "Summary", "sort_order": 4},
        ]
    }

    context = build_itinerary_render_context(rows, {"Day 1": [rows[0]], "Day 2": [rows[1]]}, {"editor_draft": editor_draft})

    assert context.render_document.page_order[:4] == ["cover", "summary", "day-day-1", "day-day-2"]

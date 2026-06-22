from pathlib import Path

from app_modules.itinerary_render_context import build_itinerary_render_context
from itinerary_generation.editor_page_contract import build_editor_document_pages


def _frontend_source() -> str:
    frontend = Path("visual_editor_component/frontend")
    return "\n".join(
        (frontend / relative).read_text(encoding="utf-8")
        for relative in (
            "styles/editor.css",
            "js/state.js",
            "js/render.js",
            "js/commands.js",
            "js/editing.js",
        )
    )


def test_outline_exposes_drag_style_page_ordering_controls():
    source = _frontend_source()

    assert "moveDocumentPage" in source
    assert "moveDocumentPageToIndex" in source
    assert "renumberDocumentPageOrders" in source
    assert "data-outline-row-page-id" in source
    assert "data-page-drag-index" in source
    assert "outline-drag-handle" in source
    assert "Drag page to reorder" in source
    assert "Page order updated" in source


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


def test_render_document_carries_saved_page_order_for_pdf_export():
    rows = [{"type": "Activity", "effective_type": "Activity", "day": "Day 1", "city": "Oslo", "title": "Walk"}]
    editor_draft = {
        "document_pages": [
            {"page_id": "day-day-1", "page_type": "generated_day", "title": "Day 1", "sort_order": 1},
            {"page_id": "cover", "page_type": "cover", "title": "Cover", "sort_order": 2},
            {"page_id": "summary", "page_type": "summary", "title": "Summary", "sort_order": 3},
        ]
    }

    context = build_itinerary_render_context(rows, {"Day 1": rows}, {"editor_draft": editor_draft})

    assert context.render_document.page_order[:3] == ["day-day-1", "cover", "summary"]

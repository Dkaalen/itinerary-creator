from pathlib import Path

from itinerary_generation.editor_page_contract import build_editor_document_pages
from tests.support.frontend_assets import frontend_source


def _frontend_source() -> str:
    return frontend_source()


def test_every_generated_page_exposes_selectable_blocks_for_inspector():
    rows = [
        {"row_id": "r1", "day": "Day 1", "type": "Activity", "effective_type": "Activity", "city": "Bergen", "title": "Fjord cruise"},
    ]
    payload = {
        "cover": {"trip_title": "Nordic Escape"},
        "summary": {"trip_glance": {"Start": "Oslo"}},
        "days": [{"day": "Day 1", "title": "Bergen", "blocks_html": "<div>Activity</div>", "image": {"name": "Bergen"}}],
        "final_pages": {"whats_not_included_html": "<ul><li>Flights</li></ul>"},
    }

    pages = build_editor_document_pages(payload=payload, grouped_days={"Day 1": rows})

    day_page = next(page for page in pages if page["page_type"] == "generated_day")
    assert day_page["generated_blocks"][0]["block_id"] == "day-day-1__main"
    assert any(block["block_type"] == "image" for block in day_page["generated_blocks"])
    assert day_page["source_row_ids"] == ("r1",)


def test_frontend_exposes_block_selection_and_right_inspector_foundation():
    source = _frontend_source()

    assert "activeBlockId" in source
    assert "activeFieldKey" in source
    assert "data-editor-block-id" in source
    assert "data-editor-page-id" in source
    assert "selectEditorBlockFromElement" in source
    assert "renderRightInspector" in source
    assert "right-inspector" in source
    assert "Selected block" in source  # legacy helper remains available outside default sidebar
    assert "Source" in source
    assert "renderInspectorTextTools" in source
    assert "Formatting" in source
    assert "renderInspectorLayoutTools" in source
    render_right = source[source.index("function renderRightInspector"):]
    assert "Selected block" not in render_right
    assert "Reset selected field" not in render_right


def test_frontend_marks_images_as_selectable_editor_blocks():
    source = _frontend_source()

    assert "data-editor-block-type=\"image\"" in source
    assert "data-editor-field-key=\"days.${dayIndex}.image\"" in source
    assert "const fieldKey = `cover.${key}`" in source
    assert "data-editor-field-key=\"${escAttr(fieldKey)}\"" in source


def test_right_inspector_exposes_pdf_safe_text_tools():
    source = _frontend_source()

    assert "renderInspectorTextTools" in source
    assert "inspectorFontFamilyPreset" in source
    assert "inspectorFontSizePreset" in source
    assert "inspectorTextStylePreset" in source
    assert "inspectorColorPreset" in source
    assert "inspectorClearFormattingBtn" in source
    assert "applyFontFamilyPreset" in source
    assert "applyFontSizePreset" in source
    assert "canUsePdfSafeTextTools" in source
    assert "Formatting applies to the selected canvas text" in source
    assert "Clear formatting" in source
    assert "text-tools-card" in source



def test_right_inspector_does_not_own_image_tools():
    source = _frontend_source()
    inspector = Path("visual_editor_component/frontend/js/editor_inspector.js").read_text(encoding="utf-8")
    images = Path("visual_editor_component/frontend/js/images.js").read_text(encoding="utf-8")
    cover_tools = Path("visual_editor_component/frontend/js/editor_image_tools.js").read_text(encoding="utf-8")

    assert "renderInspectorImageTools" not in source
    assert "inspectorImageFocus" not in source
    assert "inspectorImageBank" not in source
    assert "Why this image" not in source
    assert "Quality warnings" not in source
    assert "Replacement image" in images
    assert "data-img-action" in images
    assert "data-cover-img-action" in cover_tools
    assert "Upload" in images
    assert "Use selected" in images
    assert "Use selected" in cover_tools
    assert "image-tools-card" not in inspector

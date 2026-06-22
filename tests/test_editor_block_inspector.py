from pathlib import Path

from itinerary_generation.editor_page_contract import build_editor_document_pages


def _frontend_source() -> str:
    frontend = Path("visual_editor_component/frontend")
    return "\n".join(
        (frontend / relative).read_text(encoding="utf-8")
        for relative in (
            "styles/editor.css",
            "js/state.js",
            "js/images.js",
            "js/render.js",
            "js/commands.js",
            "js/editing.js",
        )
    )


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
    assert "Selected block" in source
    assert "Source" in source
    assert "Reset selected field" in source
    assert "Text tools" in source
    assert "Layout controls will plug into this same selected block contract next" in source


def test_frontend_marks_images_as_selectable_editor_blocks():
    source = _frontend_source()

    assert "data-editor-block-type=\"image\"" in source
    assert "data-editor-field-key=\"days.${dayIndex}.image\"" in source
    assert "data-editor-field-key=\"cover.${escAttr(key)}\"" in source


def test_right_inspector_exposes_pdf_safe_text_tools():
    source = _frontend_source()

    assert "renderInspectorTextTools" in source
    assert "inspectorTextStylePreset" in source
    assert "inspectorColorPreset" in source
    assert "inspectorClearFormattingBtn" in source
    assert "inspectorAddNoteBlockBtn" in source
    assert "inspectorAddDividerBtn" in source
    assert "canUsePdfSafeTextTools" in source
    assert "These controls write controlled classes" in source
    assert "Clear formatting" in source
    assert "text-tools-card" in source



def test_right_inspector_exposes_image_tools():
    source = _frontend_source()

    assert "renderInspectorImageTools" in source
    assert "selectedImageContext" in source
    assert "inspectorImageFocus" in source
    assert "inspectorImageBank" in source
    assert "inspectorImageAutomaticBtn" in source
    assert "inspectorImageManualBtn" in source
    assert "inspectorImageRemoveBtn" in source
    assert "inspectorImageUploadInput" in source
    assert "Why this image" in source
    assert "Quality warnings" in source
    assert "image-tools-card" in source

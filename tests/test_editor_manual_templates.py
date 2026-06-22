from pathlib import Path

from app_modules.itinerary_html import build_itinerary_html
from app_modules.itinerary_render_context import build_itinerary_render_context
from itinerary_generation.editable_draft import normalise_editable_draft


def _frontend_source() -> str:
    frontend = Path("visual_editor_component/frontend")
    return "\n".join(
        (frontend / relative).read_text(encoding="utf-8")
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
        )
    )


def test_manual_page_templates_are_available_from_outline_and_inspector():
    source = _frontend_source()

    assert "manualPageTemplateCatalog" in source
    assert "manualPageTemplateOptionsHtml" in source
    assert "manualPageTemplateSelect" in source
    assert "inspectorManualPageTemplate" in source
    assert "inspectorAddTemplatePageBtn" in source
    assert "Text page" in source
    assert "Image page" in source
    assert "Notes page" in source
    assert "Info page" in source


def test_manual_block_templates_can_be_inserted_from_inspector():
    source = _frontend_source()

    assert "manualBlockTemplateOptionsHtml" in source
    assert "manualBlockTemplate" in source
    assert "addManualBlockToSelectedPage" in source
    assert "inspectorManualBlockTemplate" in source
    assert "inspectorInsertManualBlockBtn" in source
    assert "manual_image" in source
    assert "manual_info" in source
    assert "manual_note" in source


def test_manual_template_content_uses_pdf_safe_html_contract():
    draft = normalise_editable_draft(
        {
            "document_pages": [
                {
                    "page_id": "manual-info-1",
                    "page_type": "manual",
                    "title": "Practical information",
                    "sort_order": 99,
                    "manual_blocks": [
                        {
                            "block_id": "manual-info-1__heading",
                            "block_type": "manual_heading",
                            "editable_fields": {"content_html": '<div class="section-title">Practical information</div>'},
                        },
                        {
                            "block_id": "manual-info-1__list",
                            "block_type": "manual_info",
                            "editable_fields": {"content_html": '<ul class="final-list"><li>Meeting point:</li><li>What to bring:</li></ul>'},
                        },
                    ],
                }
            ]
        }
    )
    rows = [{"type": "Activity", "effective_type": "Activity", "day": "Day 1", "city": "Oslo", "title": "Walk"}]

    html = build_itinerary_html(rows, {"Day 1": rows}, {"days": {}, "editor_draft": draft})
    context = build_itinerary_render_context(rows, {"Day 1": rows}, {"days": {}, "editor_draft": draft})

    assert "Practical information" in html
    assert "Meeting point" in html
    manual_section = next(section for section in context.render_document.final_sections if section.section_id == "manual-info-1")
    assert manual_section.pages[0].content_html

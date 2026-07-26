import json
from pathlib import Path
import subprocess
import textwrap

from app_modules.itinerary_html import build_itinerary_html
from app_modules.itinerary_render_context import build_itinerary_render_context
from itinerary_generation.editable_draft import normalise_editable_draft
from tests.support.frontend_assets import frontend_source


def _frontend_source() -> str:
    return frontend_source()


def _manual_template_snapshot() -> dict:
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');
        const context = {
          console,
          window: {},
          Date: {now: () => 1700000000000},
          document: {querySelector: () => null, querySelectorAll: () => []},
          CSS: {escape: (value) => String(value)},
          requestAnimationFrame: (fn) => fn(),
          model: {document_pages: [{page_id: 'cover', page_type: 'cover', title: 'Cover', sort_order: 1, is_hidden: false}]},
          activePageId: null,
          activeBlockId: null,
          activeFieldKey: null,
          touched: [],
          messages: [],
          notifyEditor: (message) => context.messages.push(message),
          updateRightInspector: () => {},
          collect: () => {},
          draw: () => {},
          scrollToPage: () => {},
          markTouched: (key) => context.touched.push(key),
        };
        context.ItineraryVisualEditor = {define: () => {}};
        vm.createContext(context);
        [
          'visual_editor_component/frontend/js/editor_html_utils.js',
          'visual_editor_component/frontend/js/editor_pages_model.js',
          'visual_editor_component/frontend/js/editor_layout_overrides.js',
          'visual_editor_component/frontend/js/editor_document_model.js',
          'visual_editor_component/frontend/js/editor_blocks_model.js',
          'visual_editor_component/frontend/js/editor_selection_model.js',
          'visual_editor_component/frontend/js/editor_inspector_selection.js',
          'visual_editor_component/frontend/js/editor_page_actions.js',
          'visual_editor_component/frontend/js/editor_manual_pages.js',
        ].forEach((file) => vm.runInContext(fs.readFileSync(file, 'utf8'), context, {filename: file}));
        context.scrollToPage = () => {};

        const catalog = context.manualPageTemplateCatalog();
        const infoPage = context.manualPageFromTemplate('info');
        const imageBlock = context.manualBlockTemplate('image');
        const infoBlock = context.manualBlockTemplate('info');
        context.model.document_pages.push(infoPage);
        context.activePageId = infoPage.page_id;
        context.activeBlockId = infoPage.manual_blocks[0].block_id;
        context.activeFieldKey = 'document_pages.1.manual_blocks.0.editable_fields.content_html';
        context.addManualBlockToSelectedPage('image');
        console.log(JSON.stringify({
          labels: Object.fromEntries(Object.entries(catalog).map(([key, value]) => [key, value.label])),
          pageOptions: context.manualPageTemplateOptionsHtml('info'),
          blockOptions: context.manualBlockTemplateOptionsHtml('image'),
          infoPage,
          imageBlock,
          infoBlock,
          activeFieldKey: context.activeFieldKey,
          touched: context.touched,
          blockCount: context.model.document_pages[1].manual_blocks.length,
        }));
        """
    )
    return json.loads(subprocess.check_output(["node", "-e", script], text=True))


def test_manual_page_templates_are_available_from_inspector_and_page_headers():
    snapshot = _manual_template_snapshot()

    assert snapshot["labels"]["text"] == "Text page"
    assert snapshot["labels"]["image"] == "Image page"
    assert snapshot["labels"]["notes"] == "Notes page"
    assert snapshot["labels"]["info"] == "Info page"
    assert '<option value="info" selected>Info page</option>' in snapshot["pageOptions"]
    assert snapshot["infoPage"]["page_type"] == "manual"
    assert snapshot["infoPage"]["editable_fields"]["template_id"] == "info"
    assert snapshot["infoPage"]["page_actions"]["duplicate"] is True


def test_manual_block_templates_can_be_inserted_from_inspector():
    snapshot = _manual_template_snapshot()

    assert '<option value="image" selected>Image placeholder block</option>' in snapshot["blockOptions"]
    assert snapshot["imageBlock"]["type"] == "manual_image"
    assert snapshot["infoBlock"]["type"] == "manual_info"
    assert snapshot["blockCount"] == 3
    assert snapshot["activeFieldKey"] == "document_pages.1.manual_blocks.2.editable_fields.content_html"
    assert "document_pages" in snapshot["touched"]


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

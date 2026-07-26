import json
from pathlib import Path
import subprocess
import textwrap

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
from tests.support.frontend_assets import frontend_source


def _frontend_source() -> str:
    return frontend_source()


def _page_action_snapshot() -> dict:
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
          model: {document_pages: [
            {page_id: 'cover', page_type: 'cover', title: 'Cover', sort_order: 1, is_hidden: false, page_actions: {hide: true, restore: true, move: true, duplicate: false, reset: true}},
            {page_id: 'summary', page_type: 'summary', title: 'Summary', sort_order: 2, is_hidden: false, page_actions: {hide: true, restore: true, move: true, duplicate: false, reset: true}},
          ]},
          activePageId: null,
          activeBlockId: null,
          activeFieldKey: null,
          touched: [],
          messages: [],
          pageHasDirtyEdits: () => false,
          notifyEditor: (message) => context.messages.push(message),
          updateRightInspector: () => {},
          collect: () => {},
          draw: () => {},
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
          'visual_editor_component/frontend/js/editor_document_outline.js',
          'visual_editor_component/frontend/js/editor_page_actions.js',
          'visual_editor_component/frontend/js/editor_manual_pages.js',
        ].forEach((file) => vm.runInContext(fs.readFileSync(file, 'utf8'), context, {filename: file}));

        const outline = context.renderDocumentOutline();
        const chrome = context.pageChrome('cover', 'Cover page', '<main>x</main>', {pageType: 'cover', sortOrder: 1});
        context.hideDocumentPage('summary');
        const hiddenAfterHide = context.model.document_pages.find((page) => page.page_id === 'summary').is_hidden;
        context.restoreDocumentPage('summary');
        const hiddenAfterRestore = context.model.document_pages.find((page) => page.page_id === 'summary').is_hidden;
        context.addManualPageAfter('cover', 'text');
        const ordered = context.sortedDocumentPages().map((page) => ({id: page.page_id, order: page.sort_order, type: page.page_type}));
        console.log(JSON.stringify({
          outline,
          chrome,
          hiddenAfterHide,
          hiddenAfterRestore,
          ordered,
          activePageId: context.activePageId,
          touched: context.touched,
          messages: context.messages,
        }));
        """
    )
    return json.loads(subprocess.check_output(["node", "-e", script], text=True))


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


def test_frontend_document_outline_and_page_actions_work_on_page_contract():
    snapshot = _page_action_snapshot()

    assert 'class="document-outline"' in snapshot["outline"]
    assert 'data-outline-page-id="cover"' in snapshot["outline"]
    assert 'data-doc-page-action="add-after"' in snapshot["chrome"]
    assert 'data-doc-page-action="hide"' in snapshot["chrome"]
    assert snapshot["hiddenAfterHide"] is True
    assert snapshot["hiddenAfterRestore"] is False
    assert snapshot["ordered"][1]["type"] == "manual"
    assert snapshot["ordered"][2]["id"] == "summary"
    assert snapshot["activePageId"].startswith("manual-text-")
    assert "document_pages" in snapshot["touched"]

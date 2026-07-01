from pathlib import Path

from itinerary_generation.day_intro_engine import create_day_intro
from itinerary_generation.day_titles import create_day_title


def _editor_html() -> str:
    frontend = Path("visual_editor_component/frontend")
    parts = [(frontend / "index.html").read_text(encoding="utf-8")]
    for relative in (
        "styles/editor.css",
        "js/state.js",
        "js/style_preset_data.js",
        "js/images.js",
        "js/editor_debug_shell.js",
        "js/render.js",
        "js/editor_render_final_pages.js",
        "js/serialization.js",
        "js/editor_dirty_state.js",
        "js/editor_text_tools.js",
        "js/editor_paste_sanitizer.js",
        "js/editor_html_utils.js",
        "js/editor_document_model.js",
        "js/editor_pages_model.js",
        "js/editor_inspector_selection.js",
        "js/editor_inspector_fields.js",
        "js/editor_inspector_text_panel.js",
        "js/editor_inspector_layout_panel.js",
        "js/editor_inspector.js",
        "js/editor_page_actions.js",
        "js/editor_page_event_handlers.js",
        "js/editor_warnings.js",
        "js/commands.js",
        "js/editing.js",
        "js/streamlit_bridge.js",
    ):
        parts.append((frontend / relative).read_text(encoding="utf-8"))
    return "\n".join(parts)


def test_editor_page_actions_collect_before_redraw_and_do_not_delete_nonempty_pages():
    html = _editor_html()

    assert "Move content up" in html
    assert "Remove empty page" in html
    assert "Page still has content" in html
    assert "function htmlTextContent" in html
    assert "function pageObjectAt" in html

    delete_start = html.index("function deleteInclusionPage")
    delete_body = html[delete_start : html.index("function mergeInclusionPageUp", delete_start)]
    assert "collect();" in delete_body
    assert "if (pageText)" in delete_body
    assert "return;" in delete_body
    assert "pages.splice" in delete_body

    merge_start = html.index("function mergeInclusionPageUp")
    merge_body = html[merge_start : html.index("function flagSelectedIssue", merge_start)]
    assert "collect();" in merge_body
    assert "inclusion-entry-spacer" in merge_body
    assert "pages.splice(index, 1)" in merge_body


def test_editor_toolbar_keeps_daily_surface_simple_with_advanced_tools_hidden():
    html = _editor_html()
    render_js = Path("visual_editor_component/frontend/js/render.js").read_text(encoding="utf-8")
    debug_js = Path("visual_editor_component/frontend/js/editor_debug_shell.js").read_text(encoding="utf-8")

    assert "Advanced tools" not in render_js
    assert "Advanced tools" in debug_js
    assert '<details class="advanced-tools">' in debug_js
    assert "Save changes" in html
    assert "Font" in html
    assert "Size" in html
    assert "Text color / highlight" in html
    assert "Normal text" in html
    assert "Add note block" in html
    assert "Add divider" in html

def test_editor_paste_preserves_clean_itinerary_structure_without_editor_artifacts():
    html = _editor_html()

    assert "function sanitizeClipboardHtml" in html
    assert "function plainTextToCleanPasteHtml" in html
    assert "insertCleanClipboardHtml" in html
    assert "insertHTML" in html
    assert "allowedClasses" in html
    assert "section-title" in html
    assert "inclusion-entry-title" in html
    assert "style" in html and "removeAttribute" in html
    assert "insertText" not in html


def test_hotel_only_new_destination_day_uses_welcome_wording():
    rows = [
        {
            "type": "Hotel",
            "effective_type": "Hotel",
            "day": "Day 3",
            "city": "Rovaniemi",
            "hotel_name": "Original Sokos Hotel Vaakuna Rovaniemi",
            "title": "Original Sokos Hotel Vaakuna Rovaniemi",
            "details": "2xNight, 3xStandard Room, Incl Brekafast",
        }
    ]

    assert create_day_title(rows) == "Welcome to Rovaniemi"
    assert "Welcome to Rovaniemi" in create_day_intro(rows, detail_level="Rich descriptive")
    assert "part of your stay" not in create_day_intro(rows, detail_level="Rich descriptive")

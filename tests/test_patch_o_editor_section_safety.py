from pathlib import Path

from itinerary_generation.day_intro_engine import create_day_intro
from itinerary_generation.day_titles import create_day_title


def _editor_html() -> str:
    return Path("visual_editor_component/frontend/index.html").read_text(encoding="utf-8")


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

    assert "More edit tools" in html
    assert "<details class=\"advanced-tools\">" in html
    assert "Save for now" in html
    assert "Make heading" in html
    assert "Normal text" in html


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

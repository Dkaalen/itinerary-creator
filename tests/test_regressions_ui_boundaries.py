import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TESTS_DIR))

from regression_test_helpers import assert_equal, assert_contains, assert_not_contains

from text_polish import (
    expand_time_with_duration,
    polish_client_text,
    polish_hotel_name,
    format_duration_display,
)
from generator import (
    create_whats_included,
    create_journey_arc,
    group_rows_by_day,
    create_day_intro,
    create_trip_glance,
)
from itinerary_generation.titles import create_trip_subtitle
from itinerary_parser import extract_duration_from_description, parse_itinerary
from normalizer import normalize_itinerary_rows
from layout_policy import (
    DEFAULT_DAY_PAGE_LAYOUT,
    DAY_PAGE_LAYOUTS,
    normalize_day_page_layout,
    is_day_packing_enabled,
    is_three_day_packing_enabled,
)

def test_apply_output_edits_rebuilds_activity_display_time_without_mutating_source_time():
    import types

    sys.modules.setdefault("streamlit", types.SimpleNamespace(session_state={}))
    from ui.output_edits import apply_output_edits

    rows = [
        {
            "day": "Day 1",
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Tromsø",
            "title": "Fjord Tour",
            "time": "9:00 AM",
            "duration": "5 hours 30 minutes",
        }
    ]

    edited_rows = apply_output_edits(rows, {"rows": {}})
    assert_equal(
        edited_rows[0].get("time"),
        "9:00 AM",
        "Output edit application should preserve the editable source start time.",
    )
    assert_equal(
        edited_rows[0].get("display_time"),
        "9:00 AM - 2:30 PM",
        "Output edit application should rebuild typed display-time fields after edits.",
    )


def test_visual_editor_html_sanitizer():
    from ui.editor_sanitizer import clean_visual_editor_html

    dirty = '<div class="content-block" onclick="bad()" style="color:red"><script>alert(1)</script><div class="section-title">Travel Arrangements</div><div class="body-text">Safe text</div></div>'
    clean = clean_visual_editor_html(dirty)
    assert_contains(clean, "Travel Arrangements", "Sanitizer should preserve editable day content.")
    assert_contains(clean, "Safe text", "Sanitizer should preserve body text.")
    assert_not_contains(clean.lower(), "script", "Sanitizer should remove script tags.")
    assert_not_contains(clean.lower(), "onclick", "Sanitizer should remove event attributes.")
    assert_not_contains(clean.lower(), "style=", "Sanitizer should remove inline styles.")


def test_final_page_notes_helper_is_self_contained_after_split():
    from ui.final_pages import get_important_travel_notes

    notes = get_important_travel_notes({"important_travel_notes_text": "First note\nSecond note"})
    assert_equal(
        notes,
        ["First note", "Second note"],
        "Final-page notes helper should import text conversion dependencies after module split.",
    )


def test_day_page_rendering_helpers_are_self_contained_after_split():
    from ui.day_pages import render_split_list_pages, render_text_paragraph_page

    list_html = render_split_list_pages("What’s included", ["Hotel", "Transfer"], items_per_page=10)
    assert_contains(list_html, "What’s included", "Split list pages should render after module split.")
    assert_contains(list_html, "Hotel", "Split list pages should include list items after module split.")

    notes_html = render_text_paragraph_page("Important travel notes", ["Schedules may change."])
    assert_contains(notes_html, "Important travel notes", "Text paragraph pages should render after module split.")
    assert_contains(notes_html, "Schedules may change.", "Text paragraph pages should include note text after module split.")


def test_activity_block_helpers_are_self_contained_after_split():
    from ui.day_blocks import build_activity_block

    row = {
        "type": "Activity",
        "effective_type": "Activity",
        "title": "Northern Lights Experience",
        "time": "8:00 PM",
        "duration": "2 hours",
        "includes": ["Local guide", "Northern lights search"],
    }
    block = build_activity_block(row)
    assert_contains(block["html"], "Northern Lights Experience", "Activity block should render after module split.")
    assert_contains(block["html"], "Local guide", "Activity inclusions should render after module split.")


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

def test_v36c52_content_quality_hardening_rules():
    from itinerary_generation.inclusion_sections import create_categorized_inclusions
    from itinerary_generation.inclusions import create_whats_not_included
    from ui.day_blocks import build_day_blocks, build_day_overview_block
    from generator import create_day_title

    fixtures = Path(__file__).resolve().parent / "fixtures" / "real_inputs"

    iceland_rows = normalize_itinerary_rows(parse_itinerary((fixtures / "iceland_self_drive_summer.txt").read_text(encoding="utf-8")))
    iceland_grouped = group_rows_by_day(iceland_rows)
    rental_row = next(row for row in iceland_rows if row.get("effective_type") == "Day Overview" and "Rental" in row.get("details", ""))
    rental_html = build_day_overview_block(rental_row)["html"]
    assert_contains(rental_html, "Pick up your rental SUV", "Rental pick-up should be a single polished sentence.")
    assert_contains(rental_html, "Dacia Duster or similar", "Rental block should mention one example vehicle with or similar.")
    assert_contains(rental_html, "Automatic transmission", "Rental included details should stay in the compact rental sentence.")
    assert_not_contains(rental_html, "Pick-up Rental vehicle from Office", "Rental block should not repeat raw pickup supplier text.")
    assert_not_contains(rental_html, "Vehicle category examples", "Rental day page should not list every example vehicle.")

    sections = create_categorized_inclusions(iceland_rows, iceland_grouped)
    section_titles = [section.get("title") for section in sections]
    assert_not_contains("\n".join(section_titles), "Meals included", "Hotel breakfasts should not be repeated in a separate meals section.")
    rental_section = next(section for section in sections if section.get("title") == "Rental vehicle")
    rental_text = "\n".join(rental_section.get("items", []))
    assert_contains(rental_text, "Rental SUV", "Self-drive inclusions should include a rental vehicle section.")

    scandi_rows = normalize_itinerary_rows(parse_itinerary((fixtures / "norway_sweden_denmark_summer.txt").read_text(encoding="utf-8")))
    scandi_grouped = group_rows_by_day(scandi_rows)
    day11_html = "\n".join(block["html"] for block in build_day_blocks(scandi_grouped["Day 11"]) if block)
    assert_contains(create_day_title(scandi_grouped["Day 11"]), "Train to Gothenburg", "Transport day titles should remove duplicated route text.")
    assert_not_contains(create_day_title(scandi_grouped["Day 11"]), "Gothernburg", "Known place typos should be corrected in transport titles.")
    assert_not_contains(create_day_title(scandi_grouped["Day 11"]), "Train Stockholm to", "Transport day titles should not repeat origin-destination details.")
    assert_contains(create_day_intro(scandi_grouped["Day 11"]), "Gothenburg", "Transfer intros should point to the destination city.")
    assert_not_contains(create_day_intro(scandi_grouped["Day 11"]), "towards Stockholm", "Transfer intros should not point to the origin city.")

    day13_html = "\n".join(block["html"] for block in build_day_blocks(scandi_grouped["Day 13"]) if block)
    assert_not_contains(day13_html, "included excluded", "Contradictory included/excluded text must not render.")
    assert_not_contains(day13_html, "Not included: Entrance", "Excluded entrance tickets should not appear under included experience bullets.")

    not_included = "\n".join(create_whats_not_included(scandi_rows))
    assert_contains(not_included, "Self-arranged flights or transport", "Self-arranged flights should be represented in exclusions.")

    day6_html = "\n".join(block["html"] for block in build_day_blocks(scandi_grouped["Day 6"]) if block)
    assert_not_contains(day6_html, "Stokmarknes", "Fallback descriptions must not introduce unsupported place names.")
    assert_not_contains(day6_html, ">and snacks</li>", "Natural food/drink comma phrases should not leave orphan bullets.")

    arc_text = "\n".join(item.get("experience", "") for item in create_journey_arc(scandi_grouped))
    assert_not_contains(arc_text, "Guided sightseeing", "Journey arc should use specific themes instead of repeated generic guided sightseeing.")


def test_multiline_inclusion_entries_render_pdf_visible_text():
    from ui.day_pages import render_inclusion_sections_inner_html

    html = render_inclusion_sections_inner_html([
        {"title": "Accommodation", "items": ["Hotel Arthur, Helsinki\n2 nights. Standard Room. Breakfast included."]}
    ])
    assert_contains(html, "Hotel Arthur, Helsinki", "Multiline inclusion title should render in HTML.")
    assert_contains(html, "2 nights. Standard Room. Breakfast included.", "Multiline inclusion details should render as PDF-readable body text.")
    assert_not_contains(html, '<div class="inclusion-entry">', "Multiline inclusion text should not be hidden inside unsupported wrapper elements.")
    assert_not_contains(html, "inclusion-multiline-list", "Accommodation multiline entries should remain unbulleted.")


def test_multiline_transport_inclusions_render_as_bullets():
    from ui.day_pages import render_inclusion_sections_inner_html

    html = render_inclusion_sections_inner_html([
        {"title": "Coach transfers", "items": ["Coach Transfer to Kakslauttanen\nCoach ticket included."]}
    ])
    assert_contains(html, "inclusion-multiline-list", "Multiline transport inclusions should use a bullet list for preview/PDF parity.")
    assert_contains(html, "<li>", "Multiline transport inclusions should render as bullet items.")
    assert_contains(html, "Coach Transfer to Kakslauttanen", "Coach transfer title should be visible in the bullet item.")
    assert_contains(html, "Coach ticket included.", "Coach transfer detail should be visible in the bullet item.")


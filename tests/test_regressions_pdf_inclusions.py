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



def test_hotel_dinner_stays_in_accommodation_not_meals_section():
    from itinerary_generation.inclusion_sections import create_categorized_inclusions

    raw = """
	Day 5	Transfer 		31/10/2026							Kakslauttenen	Bus : Long distance comfortable panorama coach transfer from Rovaniemi Bus Station to Kakslauttenen Arctic Resort - 11:45 am - 3:02 pm - Tickets Included
	Day 5	Hotel	1	31/10/2026	01/11/2026				Kakslauttenen	4Star, Kakslauttenen Arctic Resort  , 1xNight , 1xSmall Glass Igloo , Incl Brekafast + Dinner
"""
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    grouped = group_rows_by_day(rows)

    sections = create_categorized_inclusions(rows, grouped)
    section_titles = "\n".join(section.get("title", "") for section in sections)
    accommodation_text = "\n".join(
        item
        for section in sections
        if section.get("title") == "Accommodation"
        for item in section.get("items", [])
    )

    assert_not_contains(section_titles, "Meals included", "Hotel dinner should not create a separate meals section that repeats the accommodation name.")
    assert_contains(accommodation_text, "Kakslauttanen Arctic Resort, Kakslauttanen", "Unique stay should remain listed under accommodation.")
    assert_contains(accommodation_text, "Breakfast and dinner included.", "Hotel meal plan should stay attached to the accommodation item.")


def test_supplier_expensive_adjectives_are_grounded_in_visible_output():
    from itinerary_generation.inclusions import create_whats_not_included
    from text_polish import polish_client_text
    from ui.day_blocks import build_day_blocks

    raw = """
	Day 1	Hotel	1	01/11/2026	02/11/2026				Tromso	Premium Glass Igloo with Sauna, 1xNight, Incl Breakfast
	Day 1	Activity		01/11/2026					Tromso	Northern Lights Chase | What's included?\nPremium coach with toilet facilities\nProfessional photos from your trip
"""
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    grouped = group_rows_by_day(rows)
    day_html = "\n".join(block["html"] for block in build_day_blocks(grouped["Day 1"]) if block)
    not_included = "\n".join(create_whats_not_included(rows))

    assert_contains(day_html, "Coach with toilet facilities", "Supplier 'premium coach' wording should be grounded to the concrete coach facility.")
    assert_not_contains(day_html, "Premium coach", "Expensive-sounding supplier adjectives should not leak into client-facing day inclusions.")
    assert_not_contains(polish_client_text("Premium Glass Igloo with Sauna"), "Premium", "Room/category wording should avoid expensive-sounding adjectives where the concrete stay type is enough.")
    assert_contains(not_included, "Optional extras and personal expenses", "Exclusions should use down-to-earth wording.")
    assert_not_contains(not_included, "Optional upgrades", "Exclusions should avoid upgrade-led sales wording.")

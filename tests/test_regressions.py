import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

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


def assert_equal(actual, expected, label):
    if actual != expected:
        raise AssertionError(
            f"{label}\nExpected: {expected!r}\nActual:   {actual!r}"
        )


def assert_contains(text, expected, label):
    if expected not in text:
        raise AssertionError(
            f"{label}\nExpected to find: {expected!r}\nActual text: {text!r}"
        )


def assert_not_contains(text, unexpected, label):
    if unexpected in text:
        raise AssertionError(
            f"{label}\nDid not expect to find: {unexpected!r}\nActual text: {text!r}"
        )



def test_time_expansion():
    assert_equal(
        expand_time_with_duration("10:00 AM", "5 hours"),
        "10:00 AM - 3:00 PM",
        "Start time + duration should become a visible time range.",
    )

    assert_equal(
        extract_duration_from_description(
            "Tromsø: Fjord Tour | 9 AM | 5.5 Hrs | What's included?"
        ),
        "5 hours 30 minutes",
        "Parser should preserve decimal hour durations before display formatting.",
    )

    assert_equal(
        expand_time_with_duration("9:00 AM", "5.5 hours"),
        "9:00 AM - 2:30 PM",
        "Decimal hour durations should calculate the correct end time.",
    )

    assert_equal(
        expand_time_with_duration("10:00 AM", "1.5 hours"),
        "10:00 AM - 11:30 AM",
        "1.5 hours should calculate as 1 hour 30 minutes.",
    )

    assert_equal(
        expand_time_with_duration("8:00 PM", "6.5 hours"),
        "8:00 PM - 2:30 AM",
        "Decimal durations should cross midnight correctly.",
    )

    assert_equal(
        format_duration_display("5.5 Hrs"),
        "5 hours 30 minutes",
        "Decimal hour durations should display as clean hours and minutes.",
    )

    assert_equal(
        format_duration_display("1.5 Hrs"),
        "1 hour 30 minutes",
        "Singular duration wording should be clean.",
    )

    assert_equal(
        expand_time_with_duration("8:00 PM", "4 hours"),
        "8:00 PM - 12:00 AM",
        "Evening start time + duration should cross midnight correctly.",
    )

    assert_equal(
        expand_time_with_duration("10:30 AM - 7:30 PM", "2 hours"),
        "10:30 AM - 7:30 PM",
        "Existing time ranges should not be overwritten.",
    )

    assert_equal(
        expand_time_with_duration("10:30 AM / 1:30 PM", "2 hours"),
        "10:30 AM / 1:30 PM",
        "Alternative time options should not be overwritten.",
    )


def test_full_pasted_row_decimal_duration():
    raw = """
\tDay 9\tActivity\t\t04/10/2026\t\t\t\t\t\t\t\tTromso\t\"Tromsø: Fjord Tour of Kvaløya & Sommarøy  | 9 AM | 5.5 Hrs | What's included?

Pick-up/drop-off in central Tromsø
Knowledgeable, multilingual guide
Free photographs from the trip
2-course meal with coffee or tea\"
"""
    rows = parse_itinerary(raw)
    assert_equal(len(rows), 1, "The full pasted activity row should parse as one row.")
    assert_equal(rows[0].get("time"), "9:00 AM", "Pipe-style activity time should be extracted.")
    assert_equal(
        rows[0].get("duration"),
        "5 hours 30 minutes",
        "Full pasted rows should preserve decimal duration through parsing.",
    )
    normalized_rows = normalize_itinerary_rows(rows)
    assert_equal(
        normalized_rows[0].get("display_time"),
        "9:00 AM - 2:30 PM",
        "Display normalization should produce the final activity time range.",
    )
    assert_equal(
        normalized_rows[0].get("display_duration"),
        "5 hours 30 minutes",
        "Display normalization should preserve clean decimal duration wording.",
    )


def test_activity_includes_do_not_absorb_description_label():
    raw = """
Day 2	Activity	16.01.2027		Oslo: Oslo Center Guided Walking Tour - Time: 10:00 am - 12:00 pm - Meeting point: Near the University of Oslo - Includes: Guided walking tour, Local guide, City landmarks - Description: Explore central Oslo with a local guide, taking in key landmarks, city stories, and the atmosphere of the Norwegian capital.
"""
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    assert_equal(len(rows), 1, "The activity row should parse as one row.")
    includes = rows[0].get("includes", [])
    assert_equal(
        includes,
        ["Guided walking tour", "Local guide", "City landmarks"],
        "Includes should stop before the Description label instead of turning prose into bullets.",
    )
    assert_not_contains(
        "\n".join(includes).lower(),
        "description",
        "Description labels should not leak into inclusion bullets.",
    )


def test_text_polish_regressions():
    assert_equal(
        polish_client_text("hot drinks & snacks or cookies"),
        "Hot drinks and snacks or cookies",
        "Hot drinks inclusion should be client-facing and capitalized.",
    )

    assert_equal(
        polish_hotel_name("Santa's Hotel Santa Claus Korkalonkatu 29"),
        "Santa's Hotel Santa Claus",
        "Hotel street address should be removed from the hotel name.",
    )


def test_whats_included_nights_wording():
    rows = [
        {
            "day": "Day 1",
            "type": "Hotel",
            "effective_type": "Hotel",
            "city": "Test City",
            "hotel_name": "Test Hotel",
            "hotel_nights": "1",
            "meal_plan": "breakfast",
            "title": "Test Hotel",
            "details": "Breakfast included",
        },
        {
            "day": "Day 2",
            "type": "Departure",
            "effective_type": "Departure",
            "city": "Test City",
            "title": "Departure from Test City",
            "details": "Transfer to the airport",
        },
    ]

    grouped = group_rows_by_day(rows)
    included = create_whats_included(rows, grouped)
    joined = "\n".join(included)

    assert_contains(
        joined,
        "1 night as specified",
        "Hotel nights wording should be singular when there is 1 night.",
    )

    assert_not_contains(
        joined,
        "1 nights as specified",
        "Hotel nights wording should not use plural for 1 night.",
    )

    assert_not_contains(
        joined,
        "travel nights",
        "Hotel nights wording should not mention travel nights.",
    )


def test_journey_arc_normal_hotel_not_experience():
    rows = [
        {
            "day": "Day 1",
            "type": "Hotel",
            "effective_type": "Hotel",
            "city": "Helsinki",
            "hotel_name": "Scandic Grand Marina",
            "title": "Scandic Grand Marina",
            "details": "Standard Double Room - Breakfast included",
        }
    ]

    grouped = group_rows_by_day(rows)
    arc = create_journey_arc(grouped)
    text = " ".join(item.get("experience", "") for item in arc)

    assert_not_contains(
        text.lower(),
        "comfortable hotel stay",
        "Normal hotel stays should not be marketed as journey arc experiences.",
    )


def test_activity_intro_variation_not_templated():
    rows = [
        {
            "day": "Day 2",
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Helsinki",
            "title": "City Highlights Tour",
            "details": "Guided city sightseeing",
        }
    ]
    intro = create_day_intro(rows, detail_level="Rich descriptive")
    assert_not_contains(
        intro,
        "Today, you will enjoy",
        "Activity-led day intros should not use repeated templated wording.",
    )
    assert_not_contains(
        intro,
        "adding a meaningful experience",
        "Activity-led day intros should avoid generic filler wording.",
    )


def test_trip_glance_normal_hotels_are_arranged_accommodation():
    rows = [
        {
            "day": "Day 1",
            "type": "Hotel",
            "effective_type": "Hotel",
            "city": "Helsinki",
            "hotel_name": "Scandic Grand Marina",
            "title": "Scandic Grand Marina",
            "details": "Standard Double Room - Breakfast included",
        },
        {
            "day": "Day 2",
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Helsinki",
            "title": "City Highlights Tour",
            "details": "Guided city sightseeing",
        },
    ]
    grouped = group_rows_by_day(rows)
    glance = create_trip_glance(rows, grouped)
    assert_contains(
        glance.get("Travel Style", ""),
        "arranged accommodation",
        "Travel style should mention arranged accommodation for normal hotels.",
    )
    assert_not_contains(
        glance.get("Travel Style", ""),
        "comfortable hotel stays",
        "Normal hotels should not be marketed as comfortable hotel stays.",
    )
    assert_equal(
        glance.get("Duration", ""),
        "2 days / 1 night",
        "Trip glance should use singular night wording when appropriate.",
    )


def test_layout_policy_one_day_per_page():
    assert_equal(
        DEFAULT_DAY_PAGE_LAYOUT,
        "One day per page",
        "Premium visual layout should default to one day per A4 page.",
    )
    assert_equal(
        DAY_PAGE_LAYOUTS,
        ["One day per page"],
        "Only one-day-per-page layout should be exposed while image placement is active.",
    )
    assert_equal(
        normalize_day_page_layout("Smart compact pages"),
        "One day per page",
        "Legacy compact page settings should normalize to one-day-per-page.",
    )
    assert_equal(
        normalize_day_page_layout("3-days per page"),
        "One day per page",
        "Legacy 3-day page settings should normalize to one-day-per-page.",
    )
    assert_equal(
        is_day_packing_enabled("Smart compact pages"),
        False,
        "Day packing should be disabled for the v36 visual layout path.",
    )
    assert_equal(
        is_three_day_packing_enabled("3-days per page"),
        False,
        "Three-day packing should be disabled for the v36 visual layout path.",
    )


def test_apply_output_edits_preserves_activity_time_range_after_split():
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
        "9:00 AM - 2:30 PM",
        "Output edit application should keep activity time ranges working after module split.",
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


def test_parser_split_public_imports_remain_stable():
    from itinerary_parser import (
        clean_space,
        normalize_time_text,
        extract_duration_from_description,
        parse_itinerary,
    )
    from parser_modules.parser_main import parse_itinerary as split_parse_itinerary

    assert_equal(clean_space("  Oslo   City  "), "Oslo City", "Parser wrapper should still expose clean_space.")
    assert_equal(normalize_time_text("20:00"), "8:00 PM", "Parser wrapper should still expose time normalization.")
    assert_equal(
        extract_duration_from_description("Tromsø: Fjord Tour | 9 AM | 5.5 Hrs | What's included?"),
        "5 hours 30 minutes",
        "Parser wrapper should still expose extraction helpers after split.",
    )

    raw = "Day 1\tActivity\t01.01.2027\t\tOslo: Guided Walk - Time: 10:00 am - 12:00 pm - Includes: Guide"
    assert_equal(
        parse_itinerary(raw),
        split_parse_itinerary(raw),
        "Compatibility wrapper should return the same parser output as the split parser implementation.",
    )


def test_generator_split_public_imports_remain_stable():
    from generator import (
        create_trip_title,
        create_day_title,
        create_day_intro,
        create_whats_included,
        group_rows_by_day,
    )
    from itinerary_generation.titles import create_trip_title as split_create_trip_title
    from itinerary_generation.day_text import create_day_intro as split_create_day_intro

    raw_rows = [
        {
            "day": "Day 1",
            "type": "Arrival",
            "effective_type": "Arrival",
            "city": "Oslo",
            "title": "Welcome to Norway",
            "details": "Oslo: Welcome to Norway",
        },
        {
            "day": "Day 1",
            "type": "Hotel",
            "effective_type": "Hotel",
            "city": "Oslo",
            "title": "Hotel Bristol Oslo",
            "details": "Breakfast included",
        },
        {
            "day": "Day 2",
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Oslo",
            "title": "Northern Lights Experience",
            "details": "Northern lights search with local guide",
            "includes": ["Local guide"],
        },
    ]
    grouped = group_rows_by_day(raw_rows)
    assert_equal(create_trip_title(raw_rows, grouped), split_create_trip_title(raw_rows, grouped), "Generator wrapper should match split trip-title implementation.")
    assert_equal(create_day_intro(grouped["Day 1"]), split_create_day_intro(grouped["Day 1"]), "Generator wrapper should match split day-intro implementation.")
    assert_contains(create_day_title(grouped["Day 1"]), "Oslo", "Generator wrapper should still expose day-title helpers.")
    assert_contains("\n".join(create_whats_included(raw_rows, grouped)), "Accommodation", "Generator wrapper should still expose inclusion helpers.")


def test_day_page_editorial_parity_markup():
    from ui.day_pages import render_day_page

    rows = [{
        "day": "Day 3",
        "type": "Activity",
        "city": "Rovaniemi",
        "title": "Northern Lights Hunt",
        "description": "Northern Lights Hunt",
    }]
    html = render_day_page("Day 3", rows, image_match=None)
    assert_contains(html, "DAY 3", "Day pages should render the editorial day kicker.")
    assert_contains(html, "✦", "Day pages should keep the premium emblem separator.")
    assert_contains(html, "ROVANIEMI", "The day kicker city should render in uppercase for preview/PDF parity.")
    assert_not_contains(html, "Today’s setting", "The rejected setting label must not render on day pages.")

    final_html_css = (ROOT / "app_modules" / "itinerary_html.py").read_text(encoding="utf-8")
    assert_contains(final_html_css, ".day-image-slot::after", "Final preview should draw the emblem divider on the day image edge.")
    assert_contains(final_html_css, "box-shadow: inset 0 2px 0", "Final preview should keep the thicker divider attached to the image top edge.")
    assert_contains(final_html_css, "background: transparent", "The day-image emblem should not draw a patch behind the divider.")

    editor_html = (ROOT / "visual_editor_component" / "frontend" / "index.html").read_text(encoding="utf-8")
    assert_contains(editor_html, "day-kicker", "The visual editor preview must use the same day-kicker structure as final preview/PDF.")
    assert_contains(editor_html, "summaryStyle", "The visual editor summary page must receive the seasonal background inline.")
    assert_contains(editor_html, ".image-stage::after", "The visual editor should draw the same emblem divider on the day image edge.")
    assert_not_contains(editor_html, "Today’s setting", "The visual editor preview must not render the rejected setting label.")

def run_all():
    tests = [
        test_time_expansion,
        test_full_pasted_row_decimal_duration,
        test_activity_includes_do_not_absorb_description_label,
        test_text_polish_regressions,
        test_whats_included_nights_wording,
        test_journey_arc_normal_hotel_not_experience,
        test_activity_intro_variation_not_templated,
        test_trip_glance_normal_hotels_are_arranged_accommodation,
        test_layout_policy_one_day_per_page,
        test_apply_output_edits_preserves_activity_time_range_after_split,
        test_visual_editor_html_sanitizer,
        test_final_page_notes_helper_is_self_contained_after_split,
        test_day_page_rendering_helpers_are_self_contained_after_split,
        test_activity_block_helpers_are_self_contained_after_split,
        test_parser_split_public_imports_remain_stable,
        test_generator_split_public_imports_remain_stable,
        test_colleague_duration_with_dot_minutes,
        test_content_cleanup_for_helsinki_lapland_sample,
        test_travel_intro_uses_final_transport_destination,
        test_departure_block_avoids_duplicate_departure_line,
        test_bad_input_contextual_travel_and_activity_cleanup,
        test_trip_subtitle_uses_generic_winter_wording,
        test_seasonal_cover_title_and_subtitle_from_dates,
        test_cover_background_assets_are_available,
        test_korouoma_priority_keeps_thermal_and_barbecue,
        test_self_guided_tallinn_is_not_labeled_guided,
        test_multiline_inclusion_entries_render_pdf_visible_text,
        test_multiline_transport_inclusions_render_as_bullets,
        test_day_page_editorial_parity_markup,
    ]

    for test in tests:
        test()

    print(f"All regression tests passed ({len(tests)} tests).")



def test_colleague_duration_with_dot_minutes():
    assert_equal(
        format_duration_display("2.15 Hr"),
        "2 hours 15 minutes",
        "Supplier shorthand 2.15 Hr should mean 2 hours 15 minutes, not decimal hours.",
    )
    assert_equal(
        expand_time_with_duration("10:30 AM", "2.15 Hr"),
        "10:30 AM - 12:45 PM",
        "2.15 Hr should calculate the correct end time.",
    )




def test_trip_subtitle_uses_generic_winter_wording():
    raw = """
	Day 1	Hotel	2	14/11/2026	16/11/2026					Helsinki 	Hotel Arthur, Breakfast included
	Day 2	Activity		15/11/2026						Helsinki 	A Finntastic Walking Tour in Helsinki | Professional authorised Helsinki Guide
	Day 3	Activity		16/11/2026						Rovaniemi	Lapland Northern Lights Rapid Photo Chase | Cookies & Hot drinks
	Day 5	Hotel	1	18/11/2026	19/11/2026					Saariselka	Northern Light Village Sariselka, Incl Breakfast + Dinner
"""
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    grouped = group_rows_by_day(rows)
    subtitle = create_trip_subtitle(rows, grouped)
    assert_equal(
        subtitle,
        "A premium Nordic winter journey with scenic travel and Arctic experiences",
        "Cover subtitle should use generic premium wording instead of repeating the route.",
    )
    assert_not_contains(subtitle, "Helsinki", "Cover subtitle should not repeat destinations already shown in the Route line.")
    assert_not_contains(subtitle, "Rovaniemi", "Cover subtitle should not repeat destinations already shown in the Route line.")
    assert_not_contains(subtitle, "Saariselkä", "Cover subtitle should not repeat destinations already shown in the Route line.")
    assert_not_contains(subtitle, "Local Food", "Hotel meals should not create a food-focused subtitle theme.")
    assert_not_contains(subtitle, "—", "Cover subtitle should avoid em-dash theme chains.")


def test_seasonal_cover_title_and_subtitle_from_dates():
    from itinerary_generation.cover_theme import detect_cover_season, get_cover_theme
    from itinerary_generation.titles import create_trip_title, create_trip_subtitle

    raw = """
	Day 1	Hotel	2	10/07/2026	12/07/2026					Helsinki 	Hotel Haven, breakfast included
	Day 2	Activity		11/07/2026					Turku 	Archipelago cruise | 10:00 AM | 3 Hrs
"""
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    grouped = group_rows_by_day(rows)
    assert_equal(detect_cover_season(rows), "summer", "July itineraries should use the summer cover season.")
    assert_equal(create_trip_title(rows, grouped), "Nordic Summer Journey", "Multi-destination summer trips should get a summer cover title.")
    assert_equal(create_trip_subtitle(rows, grouped), "A premium summer journey with scenic travel and curated experiences", "Summer cover subtitle should be seasonal and generic.")

    theme = get_cover_theme(rows, {"cover_season": "winter"})
    assert_equal(theme.get("season"), "winter", "Manual cover season override should beat date detection.")


def test_cover_background_assets_are_available():
    from itinerary_generation.cover_theme import get_cover_background_path

    for season in ["winter", "spring", "summer", "autumn"]:
        path = get_cover_background_path(season)
        if not path or not path.exists():
            raise AssertionError(f"Missing cover background asset for {season}: {path}")


def test_content_cleanup_for_helsinki_lapland_sample():
    from itinerary_generation.inclusion_sections import create_categorized_inclusions

    raw = """
	Day 1	Hotel	2	14/11/2026	16/11/2026					Helsinki 	3 Star ,Hotel Arthur , 2xNight , 2x Standard Room 1xStandard Triple Room, Incl Brekafast 
	Day 2	Activity		15/11/2026						Helsinki 	A Finntastic Walking Tour in Helsinki | 10:30  AM | 2.15 Hr | Professional authorised Helsinki Guide 
	Day 3	Hotel	2	16/11/2026	18/11/2026					Rovaniemi	3 Star , Hotel Aakenus  2xNight , 3x Tirple Room, Incl Brekafast 
	Day 4	Activity		17/11/2026						Rovaniemi	Rovaniemi: Meet Santa Claus, Reindeer Ride & Greet Huskies |08:30 AM | 5 hrs

What's included?
Baby seat are provided if needed
Professional driver & guide (English)
	Day 7	Departure		20/11/2026						Helsinki 	Departure
"""
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    grouped = group_rows_by_day(rows)

    room_values = {row.get("title"): row.get("room_category") for row in rows if row.get("effective_type") == "Hotel"}
    assert_equal(
        room_values.get("Hotel Arthur"),
        "Standard Room and Standard Triple Room",
        "Multiple room categories should be separated cleanly.",
    )
    assert_equal(
        room_values.get("Hotel Aakenus"),
        "Triple Room",
        "Common room typo should be corrected.",
    )

    activity_rows = [row for row in rows if row.get("effective_type") == "Activity"]
    assert_equal(
        activity_rows[0].get("time"),
        "10:30 AM - 12:45 PM",
        "The Helsinki walking tour should display the correct time range.",
    )
    joined_includes = "\n".join(item for row in activity_rows for item in row.get("includes", []))
    assert_contains(joined_includes, "Baby seats are provided if needed", "Baby-seat text should be grammatical.")

    glance = create_trip_glance(rows, grouped)
    assert_equal(glance.get("End"), "Helsinki", "Trip glance should end at the final day city, not the last unique destination.")

    departure_intro = create_day_intro(grouped["Day 7"], detail_level="Rich descriptive")
    assert_not_contains(
        departure_intro.lower(),
        "arranged transfer",
        "Departure-only days should not invent an airport transfer.",
    )

    sections = create_categorized_inclusions(rows, grouped)
    section_titles = [section["title"] for section in sections]
    assert_contains("\n".join(section_titles), "Accommodation", "Categorized inclusions should include accommodation.")
    assert_contains("\n".join(section_titles), "Activities & experiences", "Categorized inclusions should include activities.")
    accommodation_text = "\n".join(section["items"][0] for section in sections if section["title"] == "Accommodation")
    assert_contains(accommodation_text, "Standard Room and Standard Triple Room", "Accommodation inclusions should include rooming details.")
    assert_not_contains(accommodation_text, "—", "Accommodation inclusions should avoid em-dash-heavy formatting.")


def test_travel_intro_uses_final_transport_destination():
    rows = [
        {"day": "Day 6", "type": "Transfer", "effective_type": "Transfer", "city": "Saariselkä", "title": "Coach Transfer to Rovaniemi Bus Station", "details": "Bus from Saariselkä to Rovaniemi Bus Station"},
        {"day": "Day 6", "type": "Transfer", "effective_type": "Transfer", "city": "Rovaniemi", "title": "Overnight Train to Helsinki", "details": "Overnight Train Transfer with the Santa Claus Express to Helsinki"},
    ]
    intro = create_day_intro(rows, detail_level="Rich descriptive")
    assert_contains(intro, "Saariselkä to Rovaniemi, overnight to Helsinki", "Travel intro should use a natural route label for multi-leg overnight travel.")
    assert_not_contains(intro, "towards Rovaniemi", "Travel intro should not stop at an intermediate station when later transport continues onward.")


def test_departure_block_avoids_duplicate_departure_line():
    from ui.day_blocks import build_departure_block

    block = build_departure_block({"row_id": "departure-1", "title": "Departure"})
    assert_contains(block["html"], "Journey home", "Generic departure rows should get a warmer client-facing line.")
    assert_not_contains(block["html"], '>Departure</div><div class="body-text strong-line">Departure', "Departure block should not repeat the word Departure as both heading and body.")


def test_bad_input_contextual_travel_and_activity_cleanup():
    from itinerary_generation.inclusion_sections import create_categorized_inclusions
    from ui.final_pages import clean_activity_inclusion_items, prioritize_inline_inclusions

    raw = """
	Day 2	Transfer 		14/01/2026					Helsinki 	Overnight Train : Overnight Train Transfer with the Santa Claus Express to Helsinki - 21:00 pm - 09:00 am - 1  x  downstairs cabin for two people
	Day 3	Transfer 		15/01/2026					Rovaniemi	Private Hotel to Station
	Day 3	Hotel	3	15/01/2026	18/01/2026				Rovaniemi	4 Star, Arctic City Hotel , 3xnight , 1x Standard Room , Incl breakfast 
	Day 4	Activity		16/01/2026					Rovaniemi	Rovaniemi: Santa Claus Village by Snowmobiles and Reindeer | 8 15 | 5 Hrs | Twin Driving

What's included?
Pick-up/drop-off in central Rovaniemi
Knowledgeable, English-speaking guide
Snowmobile ride: approximately 1 hour
Fun visit to Santa Claus Village
Short reindeer sleigh ride experience
Overalls, boots, gloves, balaclava & helmet
Traditional Finnish lunch buffet
	Day 7	Transfer 		19/01/2026					Rovaniemi	Bus : Long distance comfortable panorama coach transfer from Rovaniemi Bus Station to Kakslauttenen Arctic Resort - 11:45 am - 3:02 pm - Tickets Included
	Day 7	Hotel	1	19/01/2026	20/01/2026				Kakslauttenen	4 Star , kakslauttenen Arctic Resort ,  1xngiht , 1x Small Glass Igloo West or east Village , , Incl Breakfast + Dinner 
	Day 7	Activity		19/01/2026					Kakslauttenen	AURORA HUNTING WITH REINDEER |19:30 | 2 Hrs |  Include ,Transfer from and to Kakslauttanen ,Winter equipment ,Hot berry juice | Meeting point : Aurora Reception at West Village
"""
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    grouped = group_rows_by_day(rows)

    titles_by_day = {row.get("day"): row.get("title") for row in rows if row.get("effective_type") == "Train"}
    assert_equal(titles_by_day.get("Day 2"), "Overnight Train to Rovaniemi", "Overnight train destination should use next-day city context when supplier text contradicts the route.")

    day3_transfer = [row for row in rows if row.get("day") == "Day 3" and row.get("effective_type") == "Transfer"][0]
    assert_equal(day3_transfer.get("title"), "Private transfer from the station to your hotel", "Arrival-after-overnight-train context should correct hotel-to-station typos.")

    santa = [row for row in rows if row.get("day") == "Day 4" and row.get("effective_type") == "Activity"][0]
    assert_equal(santa.get("title"), "Santa Claus Village by Snowmobile & Reindeer Sleigh", "Snowmobile and reindeer titles should preserve the core activity.")
    assert_equal(santa.get("time"), "8:15 AM - 1:15 PM", "Spaced times such as 8 15 should parse as 8:15 AM and expand with duration.")
    santa_inline = prioritize_inline_inclusions(clean_activity_inclusion_items(santa.get("includes", []), santa.get("title")), 5)
    santa_inline_text = "\n".join(santa_inline)
    assert_contains(santa_inline_text, "Short reindeer sleigh ride experience", "Important reindeer ride inclusion should survive compact day-page prioritization.")
    assert_contains(santa_inline_text, "Winter equipment provided", "Winter equipment should survive compact day-page prioritization.")
    assert_contains(santa_inline_text, "Traditional Finnish lunch buffet", "Included lunch should survive compact day-page prioritization.")
    assert_not_contains(santa_inline_text, "Knowledgeable, English-speaking guide", "Generic guide wording should be dropped before included meals when the day-page list is capped.")

    reindeer_hunt = [row for row in rows if row.get("day") == "Day 7" and row.get("effective_type") == "Activity"][0]
    assert_equal(reindeer_hunt.get("title"), "Northern Lights Hunt by Reindeer", "Aurora wording should become Northern Lights while preserving the reindeer differentiator.")
    assert_contains("\n".join(reindeer_hunt.get("includes", [])), "Transfer to and from Kakslauttanen", "Pipe-style Include sections should parse transfer inclusions.")
    assert_contains("\n".join(reindeer_hunt.get("includes", [])), "Hot berry juice", "Pipe-style Include sections should parse hot berry juice.")

    day7_intro = create_day_intro(grouped["Day 7"], detail_level="Rich descriptive")
    assert_contains(day7_intro, "Kakslauttanen", "Travel-day intro should identify the actual onward destination, not the origin city.")
    assert_not_contains(day7_intro, "towards Rovaniemi", "Travel-day intro should not point back to the origin city.")

    sections = create_categorized_inclusions(rows, grouped)
    section_titles = [section.get("title") for section in sections]
    assert_not_contains("\n".join(section_titles), "Guides & local support", "Guide-support summaries should not repeat or misstate self-guided activity details.")
    all_inclusions = "\n".join(item for section in sections for item in section.get("items", []))
    assert_contains(all_inclusions, "Arctic City Hotel, Rovaniemi", "Accommodation section should include hotel entries.")
    assert_contains(all_inclusions, "Small Glass Igloo, West or East Village", "Room category cleanup should polish glass igloo village wording.")
    assert_contains(all_inclusions, "Coach Transfer to Kakslauttanen", "Coach transfer section should include the arranged coach transfer.")
    assert_contains(all_inclusions, "Northern Lights Hunt by Reindeer", "Separate reindeer Northern Lights activity should not be deduplicated away.")


def test_korouoma_priority_keeps_thermal_and_barbecue():
    from ui.final_pages import clean_activity_inclusion_items, prioritize_inline_inclusions

    title = "Korouoma Frozen Waterfalls Hike & BBQ"
    raw_items = [
        "Pick-up/drop-off in central Rovaniemi",
        "Transfers in brand-new 2025 Ford Tourneo",
        "Professional and certified guide",
        "Thermal overalls to keep you warm",
        "4–6 km guided hike in Korouoma Canyon",
        "Small groups (max 8 guests)",
        "Hot drinks & barbecue",
    ]

    compact = prioritize_inline_inclusions(clean_activity_inclusion_items(raw_items, title), 5)
    compact_text = "\n".join(compact)

    assert_contains(compact_text, "Pick-up/drop-off in central Rovaniemi", "Korouoma inclusions should keep pick-up/drop-off logistics.")
    assert_contains(compact_text, "Thermal overalls to keep you warm", "Korouoma inclusions should keep thermal equipment.")
    assert_contains(compact_text, "4–6 km guided hike in Korouoma Canyon", "Korouoma inclusions should keep the signature guided hike.")
    assert_contains(compact_text, "Hot drinks & barbecue", "Korouoma inclusions should keep the BBQ/hot drinks item.")
    assert_not_contains(compact_text, "Small groups", "Group-size details should not take compact day-page inclusion space.")


def test_self_guided_tallinn_is_not_labeled_guided():
    from ui.final_pages import get_fallback_activity_inclusions

    row = {
        "title": "Day Trip to Tallinn",
        "original_title": "Excursion to Tallinn - Helsinki Port transfers included (hotel pick up and drop off) - Self guided tour of Old Town Tallinn - Time: 10:30 am - 07:30 pm Cruise Duration 2 Hr",
        "details": "Self guided tour of Old Town Tallinn",
        "includes": [],
    }
    inclusions = get_fallback_activity_inclusions(row)
    inclusion_text = "\n".join(inclusions)
    assert_contains(inclusion_text, "Self-guided Old Town visit", "Self-guided Tallinn visits should be labeled as self-guided.")
    assert_not_contains(inclusion_text, "Guided Old Town tour", "Self-guided Tallinn visits should not be mislabeled as guided tours.")


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


if __name__ == "__main__":
    run_all()



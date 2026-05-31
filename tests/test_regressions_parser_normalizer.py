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


def test_duration_ranges_are_preserved_for_display():
    assert_equal(
        format_duration_display("Duration 2.5 -3.5h with panoramic views"),
        "2.5–3.5 hours",
        "Explicit duration ranges should not collapse to the upper bound.",
    )


def test_hotel_name_before_room_marker_is_parsed_generally():
    raw = """
	Day 5	Hotel	1	13/07/2026	14/07/2026				Öræfi	Fosshotel Glacier Lagoon 1x Standard Room - Triple , incl breakfast
"""
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    row = rows[0]
    assert_equal(row.get("hotel_name"), "Fosshotel Glacier Lagoon", "Hotel parser should split hotel name before room count markers.")
    assert_equal(row.get("room_category"), "1 x Standard Room - Triple", "Room parser should preserve room-count prefix.")


def test_place_alias_normalization_does_not_duplicate_suffixes_or_common_words():
    from place_aliases import normalize_place_text
    text = normalize_place_text("Thingvellir National Park is beautiful. Our tours are unique.")
    assert_contains(text, "Þingvellir National Park", "Known place aliases should still normalize.")
    assert_not_contains(text, "National Park National Park", "Place aliases should not duplicate canonical suffixes.")
    assert_contains(text, "tours are unique", "Common English words should not be rewritten as place aliases.")


def test_context_city_fill_prevents_journey_chapters():
    fixtures = Path(__file__).resolve().parent / "fixtures" / "real_inputs"
    raw = (fixtures / "finland_norway_winter_variant.txt").read_text(encoding="utf-8")
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    grouped = group_rows_by_day(rows)
    day2 = grouped.get("Day 2", [])
    assert day2, "Fixture should include Day 2."
    assert_contains("\n".join(row.get("city", "") for row in day2), "Helsinki", "City should be inferred from itinerary context when supplier leaves the city cell blank.")
    chapters = create_journey_arc(grouped)
    chapter_names = "\n".join(chapter.get("chapter", "") for chapter in chapters)
    assert_not_contains(chapter_names, "Journey", "Known same/previous-city context should prevent generic Journey chapters.")


def test_optional_addon_inclusion_fragments_are_merged():
    from ui.final_pages import create_optional_addons

    fixtures = Path(__file__).resolve().parent / "fixtures" / "real_inputs"
    raw = (fixtures / "finland_norway_autumn_alta.txt").read_text(encoding="utf-8")
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    addons = create_optional_addons(rows)
    assert addons, "Optional add-ons should be extracted from the fixture."
    include_text = "\n".join(item for addon in addons for item in addon.get("includes", []))
    assert_contains(include_text, "Rental of warm thermal suits, boots, gloves, balaclava & goggles", "Thermal suit gear fragments should merge into one optional add-on inclusion.")
    assert_not_contains(include_text, "\nboots", "Boots should not render as an orphan optional add-on bullet.")


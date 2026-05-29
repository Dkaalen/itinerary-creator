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
        "A Finland winter journey with scenic travel and planned experiences",
        "Single-country cover subtitle should use country-specific down-to-earth wording instead of repeating the route.",
    )
    assert_not_contains(subtitle, "Helsinki", "Cover subtitle should not repeat destinations already shown in the Route line.")
    assert_not_contains(subtitle, "Rovaniemi", "Cover subtitle should not repeat destinations already shown in the Route line.")
    assert_not_contains(subtitle, "Saariselkä", "Cover subtitle should not repeat destinations already shown in the Route line.")
    assert_not_contains(subtitle, "Local Food", "Hotel meals should not create a food-focused subtitle theme.")
    assert_not_contains(subtitle, "—", "Cover subtitle should avoid em-dash theme chains.")


def test_semantic_casing_normalizes_group_tour_phrases():
    from text_polish import polish_client_text, polish_title

    examples = {
        "south Coast & Katla Ice Cave": "South Coast & Katla Ice Cave",
        "eastfjords & Local Life": "Eastfjords & Local Life",
        "north Iceland": "North Iceland",
        "whale Watching": "Whale Watching",
    }
    for raw, expected in examples.items():
        assert polish_client_text(raw) == expected
        assert polish_title(raw) == expected



def test_generated_client_language_avoids_expensive_sounding_terms():
    from itinerary_generation.summaries import create_trip_glance
    from itinerary_generation.titles import create_client_activity_title

    raw = """
	Day 1	Hotel	2	10/07/2026	12/07/2026						Helsinki 	Hotel Haven, breakfast included
	Day 1	Activity		10/07/2026							Bluelagoon	Blue Lagoon Premium Entry tickets
	Day 2	Activity		11/07/2026							Turku 	Archipelago cruise | 10:00 AM | 3 Hrs
"""
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    grouped = group_rows_by_day(rows)

    generated = "\n".join(
        [
            create_trip_subtitle(rows, grouped),
            create_trip_glance(rows, grouped)["Travel Style"],
            create_client_activity_title(next(row for row in rows if "blue lagoon" in f'{row.get("title", "")} {row.get("details", "")}'.lower())),
        ]
    ).lower()

    for forbidden in ["premium", "luxury", "luxurious", "high-end", "hi-end", "upscale", "curated", "bespoke", "vip"]:
        assert forbidden not in generated

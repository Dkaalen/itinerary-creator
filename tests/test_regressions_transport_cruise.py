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

def test_v36c54_transport_cruise_inclusion_quality_gate():
    from itinerary_generation.inclusion_sections import create_categorized_inclusions
    from itinerary_generation.inclusions import create_whats_not_included
    from itinerary_generation.titles import create_day_title
    from itinerary_generation.day_text import create_day_intro
    from ui.day_blocks import build_day_blocks
    from ui.day_pages import render_categorized_inclusions_pages

    short_norway = """
	Day 1	Transfer 		05/06/2026					Oslo	Private Airport to Hotel
	Day 1	Hotel	2	05/06/2026	07/06/2026				Oslo	3 Star, Scandic St Olavs Plass , 2xNight , 1xStandard Family Quadruple room , Incl Brekafast (City Centre )
	Day 3	Activity		07/06/2026					Bergen	Train : Oslo to Bergen | 14:25 - 21:33 |
	Day 3	Hotel	2	07/06/2026	09/06/2026				Bergen	3 Star, Scandic Bergen City, 2xNight, 1xFamily Room, Incl Brekafast
	Day 5	Transfer 	1	09/06/2026	10/06/2026				Bergen	Overngiht Cruise , Bergen to Alesund | 1x Cabin ( Polar Outside ) | Tuesday 09 Jun 2026 8:30 pm Wednesday 10 Jun 2026 9:45 am
	Day 6	Hotel	1	10/06/2026	11/06/2026				Alesund	4 Star, Quality Hotel Ålesund, 1xNight, 1xStandard Family Room, Incl Brekafast
"""
    rows = normalize_itinerary_rows(parse_itinerary(short_norway))
    grouped = group_rows_by_day(rows)

    assert_equal(create_day_title(grouped["Day 3"]), "Train to Bergen", "Point-to-point train rows pasted as activities should become transport day titles.")
    day3_html = "\n".join(block["html"] for block in build_day_blocks(grouped["Day 3"]) if block)
    assert_contains(day3_html, "Scenic Train Transfer from Oslo to Bergen", "Train rows should render as clear travel arrangements, not activities.")
    assert_not_contains(day3_html, "Afternoon Experience", "Train transfers should not render as experience blocks.")

    day5_html = "\n".join(block["html"] for block in build_day_blocks(grouped["Day 5"]) if block)
    assert_contains(day5_html, "Overnight Coastal Cruise from Bergen to Ålesund", "Overnight cruise routes should preserve origin and destination with clear cruise wording.")
    assert_contains(day5_html, "Polar Outside cabin", "Overnight cruise cabin details should be preserved where provided.")
    assert_not_contains(day5_html, "Overngiht", "Common cruise typos should be cleaned before rendering.")

    fixtures = Path(__file__).resolve().parent / "fixtures" / "real_inputs"
    cruise_rows = normalize_itinerary_rows(parse_itinerary((fixtures / "scandinavia_autumn_cruise.txt").read_text(encoding="utf-8")))
    cruise_grouped = group_rows_by_day(cruise_rows)
    day4_html = "\n".join(block["html"] for block in build_day_blocks(cruise_grouped["Day 4"]) if block)
    assert_equal(create_day_title(cruise_grouped["Day 4"]), "Train to Stockholm", "Multi-leg rail days should title the final destination, not the intermediate change point.")
    assert_contains(create_day_intro(cruise_grouped["Day 4"], detail_level="Rich descriptive"), "Stockholm", "Multi-leg train intros should point to the final destination.")
    assert_contains(day4_html, "Scenic Train Transfer from Copenhagen to Stockholm, via Malmö", "Multi-leg rail routes should preserve the intermediate change point without becoming the title.")

    day8_intro = create_day_intro(cruise_grouped["Day 8"], detail_level="Rich descriptive")
    assert_contains(day8_intro, "Bergen", "Cruise start intros should point towards the cruise destination.")
    assert_not_contains(day8_intro, "towards Kirkenes", "Cruise start intros should not point back to the origin port.")
    assert_equal(create_day_title(cruise_grouped["Day 13"]), "Cruise arrival to Bergen", "Cruise arrival day titles should preserve arrival wording.")
    day13_html = "\n".join(block["html"] for block in build_day_blocks(cruise_grouped["Day 13"]) if block)
    assert_contains(day13_html, "Cruise arrival to Bergen", "Cruise arrival should render as an arrival, not another generic cruise to Bergen.")
    assert_contains(day13_html, "2:45 PM", "Cruise arrival times should be preserved when supplied.")

    sections = create_categorized_inclusions(cruise_rows, cruise_grouped)
    inclusion_text = "\n".join(item for section in sections for item in section.get("items", []))
    assert_not_contains(inclusion_text, "Spend time at leisure onboard the cruise", "Cruise leisure days should not be commercial inclusions.")
    assert_not_contains(inclusion_text, "Self transfer", "Self transfers must never appear in the inclusions list.")
    pages_html = render_categorized_inclusions_pages("What’s included", sections)
    assert_contains(pages_html, "What’s included continued", "Long categorized inclusions should split into explicit continued pages instead of orphan bullets.")

    alta_rows = normalize_itinerary_rows(parse_itinerary((fixtures / "finland_norway_autumn_alta.txt").read_text(encoding="utf-8")))
    alta_grouped = group_rows_by_day(alta_rows)
    alta_sections = create_categorized_inclusions(alta_rows, alta_grouped)
    alta_inclusion_text = "\n".join(item for section in alta_sections for item in section.get("items", []))
    assert_not_contains(alta_inclusion_text, "Self transfer", "Self transfers should remain day logistics only, not included services.")
    assert_contains("\n".join(create_whats_not_included(alta_rows)), "Optional add-ons", "Optional add-ons should remain commercially clear in exclusions.")


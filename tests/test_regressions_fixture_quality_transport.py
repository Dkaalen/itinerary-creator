import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TESTS_DIR))

from regression_test_helpers import assert_equal, assert_contains, assert_not_contains

from generator import (
    create_day_title,
    group_rows_by_day,
)
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows


def test_optional_arc_transfer_quality_gate():
    from generator import create_day_title, create_journey_arc
    from itinerary_generation.inclusion_sections import create_categorized_inclusions
    from itinerary_generation.inclusions import create_whats_not_included
    from itinerary_generation.titles import create_client_activity_title
    from ui.day_blocks import build_day_blocks
    from ui.render_helpers import get_activity_description

    fixtures = Path(__file__).resolve().parent / "fixtures" / "real_inputs"
    # Strict Journey Arc gate: every real fixture should remain compact enough
    # for the summary table instead of wrapping into long keyword lists.
    for fixture_path in sorted(fixtures.glob("*.txt")):
        fixture_rows = normalize_itinerary_rows(parse_itinerary(fixture_path.read_text(encoding="utf-8")))
        fixture_grouped = group_rows_by_day(fixture_rows)
        for chapter in create_journey_arc(fixture_grouped):
            assert len(chapter.get("experience", "")) <= 48, f"Journey Arc row too long in {fixture_path.name}: {chapter!r}"
            assert_not_contains(chapter.get("experience", ""), "local food culture, scenic nature experiences", "Arc phrases should not be long keyword lists.")
            assert_not_contains(chapter.get("chapter", ""), "Journey", "Known cruise/service chapters should use a more specific chapter label.")

    raw = (fixtures / "finland_norway_autumn_alta.txt").read_text(encoding="utf-8")
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    grouped = group_rows_by_day(rows)

    day4_titles = [row.get("title") for row in grouped["Day 4"] if row.get("effective_type") == "Activity"]
    assert_contains("\n".join(day4_titles), "Santa Claus Village & Reindeer Visit", "The first Day 4 activity should remain visible.")
    assert_contains("\n".join(day4_titles), "Small-Group Northern Lights Hunt by Minibus", "The second Day 4 activity must not be skipped by trailing spreadsheet markers.")

    day8_title = create_day_title(grouped["Day 8"])
    assert_equal(day8_title, "Coach Transfer to Alta", "Coach transfer days should title the actual destination, not the origin city.")
    day8_html = "\n".join(block["html"] for block in build_day_blocks(grouped["Day 8"]) if block)
    assert_contains(day8_html, "Self transfer from your hotel to the bus station", "Self transfers to bus station should be labeled as self transfers, not self-guided transfers.")
    assert_not_contains(day8_html, "Self-guided transfer", "Self transfer wording should not use the confusing self-guided label.")
    assert_contains(day8_html, "Panoramic Coach Transfer from Tromsø to Alta", "Coach transfer should preserve the actual route to Alta with clear wording.")
    assert_not_contains(day8_html, "Coach Transfer to Tromsø", "Coach transfer should not point back to the origin city.")

    optional_rows = [row for row in rows if row.get("is_optional")]
    assert optional_rows, "Optional add-on rows should be detected even when Optional Addon appears inside the activity cell."
    optional_title = create_client_activity_title(optional_rows[0])
    assert_equal(optional_title, "Whale Watching & Arctic Wildlife Safari by RIB Boat", "Optional whale/RIB add-ons should keep their specific title.")
    assert "Day 9" in grouped, "The main Day 9 should remain after optional add-ons are excluded from grouped days."
    day9_titles = "\n".join(row.get("title", "") for row in grouped["Day 9"])
    assert_not_contains(day9_titles, "Optional Addon", "Optional add-ons must not appear as normal included day activities.")
    assert_not_contains(day9_titles, "Whale Watching", "Optional whale watching must not become the main day title.")

    inclusions = "\n".join(item for sec in create_categorized_inclusions(rows, grouped) for item in sec.get("items", []))
    assert_not_contains(inclusions, "Whale Watching & Arctic Wildlife Safari", "Optional add-ons must not appear in normal inclusions.")
    assert_not_contains(inclusions, "Whale Watching From Downtown", "Generic whale title should not leak for the optional Alta RIB safari.")
    assert_contains(inclusions, "Northern Lights Tour by Minibus with Photo Assistance", "The included Alta northern lights activity should remain included with its source-specific title.")

    not_included = "\n".join(create_whats_not_included(rows))
    assert_contains(not_included, "Optional add-ons and experiences", "Optional add-ons should be commercially clear in exclusions.")
    assert_contains(not_included, "Tickets or services marked as excluded", "Excludes/tickets on-site notes should reach exclusions.")
    assert_contains(not_included, "Self-arranged flights or transport", "Self-arranged flight/transport rows should reach exclusions.")

    reindeer = next(row for row in rows if "Reindeer Feeding" in row.get("title", ""))
    reindeer_desc = get_activity_description(reindeer)
    assert_contains(reindeer_desc, "Sámi culture", "Reindeer/Sámi descriptions should focus on culture and herd experience.")
    assert_not_contains(reindeer_desc, "Northern Lights hunt by reindeer", "Daytime reindeer/Sámi culture should not be mislabeled as a northern lights hunt.")

    alta_nl = next(row for row in rows if row.get("city") == "Alta" and "Northern Lights" in row.get("title", ""))
    alta_inclusions = "\n".join(alta_nl.get("includes", []))
    assert_contains(alta_inclusions, "Camera assistance, camera tripods", "Camera assistance/tripods should not split into orphan bullets.")

    cruise_raw = (fixtures / "scandinavia_autumn_cruise.txt").read_text(encoding="utf-8")
    cruise_rows = normalize_itinerary_rows(parse_itinerary(cruise_raw))
    cruise_grouped = group_rows_by_day(cruise_rows)
    day9_cruise_html = "\n".join(block["html"] for block in build_day_blocks(cruise_grouped["Day 9"]) if block)
    assert_contains(day9_cruise_html, "Spend time at leisure onboard the cruise", "Cruise leisure days should use onboard cruise wording, not a generic Cruise label.")
    assert_not_contains(day9_cruise_html, ">Cruise<", "Cruise-only leisure days should not render as a vague Cruise row.")
    day13_cruise_title = create_day_title(cruise_grouped["Day 13"])
    assert_contains(day13_cruise_title, "Cruise arrival to Bergen", "Cruise arrival days should mention the arrival city instead of a generic Cruise title.")


def test_clear_transport_wording_system():
    from ui.day_blocks import build_day_blocks
    from itinerary_generation.inclusion_sections import create_categorized_inclusions

    raw = """
	Day 1	Activity		05/06/2026								Bergen	Train : Oslo to Bergen | 14:25 - 21:33 |
	Day 2	Train		06/06/2026								Stockholm	Copenhagen: Scenic Train Transfer to Malmø to Stockholm - Departure from Copenhagen: 1:59 pm - Arrival in Malmø: 2:40 pm - Departure from Malmø: 3:07 pm - Arrival in Stockholm: 7:35 pm - Includes: First class tickets
	Day 3	Transfer		07/06/2026								Alta	Tromsø: Long distance panorama coach transfer to Alta - Bus 150 - Time: 4:00 pm - 10:20 pm
	Day 4	Flight		08/06/2026								Kirkenes	Stockholm: Flight to Kirkenes, via Oslo - Time: 4:10 pm - 8:30 pm - Includes: Flex tickets, luggage
	Day 5	Cruise		09/06/2026	10/06/2026						Bergen	Kirkenes: Atlantic Ocean Cruise to Bergen onboard MC Havila Castor - Departure from Kirkenes: 12:30 pm - Includes: Balcony Suite, Full Pension Meal plan
"""
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    grouped = group_rows_by_day(rows)
    html = "\n".join("\n".join(block["html"] for block in build_day_blocks(day_rows) if block) for day_rows in grouped.values())
    assert_contains(html, "Scenic Train Transfer from Oslo to Bergen", "Point-to-point rail should use clear scenic transfer wording.")
    assert_contains(html, "Scenic Train Transfer from Copenhagen to Stockholm, via Malmö", "Multi-leg rail should keep the final destination and via stop.")
    assert_contains(html, "Panoramic Coach Transfer from Tromsø to Alta", "Panoramic/long-distance coach rows should use clear coach wording.")
    assert_contains(html, "Flight from Stockholm to Kirkenes, via Oslo", "Flights should preserve via-city wording.")
    assert_contains(html, "Coastal Cruise from Kirkenes to Bergen onboard MC Havila Castor", "Cruise rows should use clear cruise wording with ship name when present.")

    sections = create_categorized_inclusions(rows, grouped)
    inclusion_text = "\n".join(item for section in sections for item in section.get("items", []))
    assert_contains(inclusion_text, "Scenic Train Transfer from Oslo to Bergen", "Rail inclusions should use the same clear wording as day pages.")
    assert_contains(inclusion_text, "Flight from Stockholm to Kirkenes, via Oslo", "Flight inclusions should use clear route wording.")
    assert_contains(inclusion_text, "Coastal Cruise from Kirkenes to Bergen onboard MC Havila Castor", "Cruise inclusions should use clear route wording.")


def test_real_uploaded_inputs_quality_gate():
    from itinerary_generation.inclusion_sections import create_categorized_inclusions
    from itinerary_generation.titles import create_client_activity_title, create_trip_title
    from itinerary_generation.summaries import create_journey_arc
    from ui.day_blocks import build_day_blocks
    from ui.day_pages import render_categorized_inclusions_pages
    from ui.final_pages import create_optional_addons, render_optional_addons_pages

    fixtures = Path(__file__).resolve().parent / "fixtures" / "real_inputs"

    family_rows = normalize_itinerary_rows(parse_itinerary((fixtures / "norway_finland_family_autumn.txt").read_text(encoding="utf-8")))
    family_grouped = group_rows_by_day(family_rows)

    winter_family_rows = normalize_itinerary_rows(parse_itinerary((fixtures / "finland_norway_winter_family.txt").read_text(encoding="utf-8")))
    winter_family_grouped = group_rows_by_day(winter_family_rows)
    winter_room_text = "\n".join(row.get("room_category", "") for row in winter_family_rows if row.get("effective_type") == "Hotel")
    assert_contains(winter_room_text, "2 x Family Room (for 2 adults and 2 kids)", "Family-room quantities and occupancy notes should survive hotel normalization.")
    assert_contains(winter_room_text, "1 x Junior Suite (for 3 adults)", "Junior-suite quantities should not be lost from multi-room hotel rows.")
    assert_contains(winter_room_text, "2 x Igloo with alcove (for 2 adults and 2 kids)", "Igloo-with-alcove quantities should survive hotel normalization.")
    assert_equal(create_day_title(winter_family_grouped["Day 5"]), "Glass Igloo Stay in Rovaniemi", "Hotel-only relocation days should not use raw private-transfer copy as the day heading.")

    santa_row = next(row for row in family_rows if "SANTA CLAUS" in row.get("original_title", "") or "Santa Claus" in row.get("title", ""))
    assert_equal(create_client_activity_title(santa_row), "Meet Santa Claus and his friends", "Santa activity titles should use grammatical sentence-style capitalization.")
    day9_html = "\n".join(block["html"] for block in build_day_blocks(family_grouped["Day 9"]) if block)
    assert_contains(day9_html, "Meet Santa Claus and his friends", "The day block should render the grammatical Santa title.")
    assert_not_contains(day9_html, "Meet Santa Claus and His Friends", "The day block should not keep supplier title case.")

    family_addons = create_optional_addons(family_rows)
    assert family_addons, "The family fixture should detect the optional cod tasting add-on."
    addon_text = render_optional_addons_pages(family_addons)
    assert_contains(addon_text, "Norwegian Cod Tasting", "Optional add-on description should remain visible.")
    for forbidden in ["56 EUR", "EUR/Person", "Price is per passenger", "Cost:", "Price:"]:
        assert_not_contains(addon_text, forbidden, "Optional add-on pages must never expose prices.")
    family_sections = create_categorized_inclusions(family_rows, family_grouped)
    family_inclusions = "\n".join(item for section in family_sections for item in section.get("items", []))
    assert_not_contains(family_inclusions, "Norwegian Cod Tasting", "Optional add-ons should not appear in included services.")

    scandi_rows = normalize_itinerary_rows(parse_itinerary((fixtures / "scandinavia_cruise_premium_working.txt").read_text(encoding="utf-8")))
    scandi_grouped = group_rows_by_day(scandi_rows)
    nutshell_row = next(row for row in scandi_rows if "Flåm Train" in row.get("original_title", "") or "Nærøyfjord" in row.get("original_title", ""))
    assert_equal(create_client_activity_title(nutshell_row), "Norway in a Nutshell from Bergen to Oslo", "Route-style Nutshell products should normalize to the product name with route.")
    day16_html = "\n".join(block["html"] for block in build_day_blocks(scandi_grouped["Day 16"]) if block)
    assert_contains(day16_html, "Norway in a Nutshell from Bergen to Oslo", "Day page should use normalized Nutshell title.")
    assert_not_contains(day16_html, "Day Tour incl.", "Raw supplier Nutshell title should not leak into the day block.")

    iceland_rows = normalize_itinerary_rows(parse_itinerary((fixtures / "iceland_group_tour_winter.txt").read_text(encoding="utf-8")))
    iceland_grouped = group_rows_by_day(iceland_rows)
    iceland_arc = create_journey_arc(iceland_grouped)
    iceland_arc_text = "\n".join(item["experience"] for item in iceland_arc)
    assert_contains(iceland_arc_text, "Borgarfjörður valley and waterfalls", "Iceland group-tour day headings should drive the Journey Arc, not generic Northern Lights text.")
    assert_contains(iceland_arc_text, "Blue Lagoon experience", "Blue Lagoon days should be summarized specifically, not as generic lagoon and wellness repetition.")
    assert_equal(create_trip_title(iceland_rows, iceland_grouped), "Snæfellsnes & South Coast Adventure", "Iceland group tour should keep its group-tour trip title.")
    assert "Day 9" in iceland_grouped, "Iceland fixture should parse all pasted group-tour days."
    blue_lagoon_row = next(row for row in iceland_rows if "Blue Lagoon" in row.get("title", "") or "Blue Lagoon" in row.get("original_title", ""))
    assert_equal(create_client_activity_title(blue_lagoon_row), "Blue Lagoon & Volcano Eruption Site Tour", "Combo Blue Lagoon products should keep the full experience title instead of becoming a generic admission.")
    iceland_sections = create_categorized_inclusions(iceland_rows, iceland_grouped)
    iceland_output_text = "\n".join(item for section in iceland_sections for item in section.get("items", []))
    assert_not_contains(iceland_output_text, "Single traveler supplement fee €500", "Group-tour commercial supplements must not leak into client-facing inclusions.")

    # Synthetic stress case for the inclusion pagination rule: if a category is
    # too large for one page, it is split with a repeated category heading.
    huge_section = {"title": "Activities & experiences", "items": [f"Included experience number {index} with guide, tickets and transfers" for index in range(1, 52)]}
    huge_html = render_categorized_inclusions_pages("What’s included", [huge_section])
    assert_contains(huge_html, "What’s included", "Oversized inclusion sections should still create inclusion pages.")
    assert_not_contains(huge_html, "What’s included continued", "Repeated inclusion pages should keep the clean page title without 'continued' wording.")
    assert_contains(huge_html, "Activities &amp; experiences", "Split oversized categories should keep their category heading.")
    assert_not_contains(huge_html, "Activities &amp; experiences continued", "Split categories should not add ugly continued wording.")
    assert huge_html.count('categorized-inclusions-page') >= 2

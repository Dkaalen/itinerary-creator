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
    create_day_title,
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
        "2 x Standard Room, 1 x Standard Triple Room",
        "Multiple room categories should be separated cleanly.",
    )
    assert_equal(
        room_values.get("Hotel Aakenus"),
        "3 x Triple Room",
        "Common room typo and quantity should be corrected.",
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
    assert_contains(accommodation_text, "2 x Standard Room, 1 x Standard Triple Room", "Accommodation inclusions should include room quantities and categories.")
    assert_not_contains(accommodation_text, "—", "Accommodation inclusions should avoid em-dash-heavy formatting.")


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
    assert_contains(all_inclusions, "Panoramic Coach Transfer from Rovaniemi Bus Station to Kakslauttanen", "Coach transfer section should include the arranged coach transfer with clear route wording.")
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


def test_generalized_iceland_self_drive_logic():
    from generator import create_trip_title, create_destinations_line, create_trip_glance
    from itinerary_generation.titles import create_client_activity_title
    from ui.render_helpers import get_activity_description

    raw = """
	Day 1	Transfer 		09/07/2026					Keflavik 	Arrival in Keflavik at 04:30 PM
	Day 1	Day overview		09/07/2026					Keflavik 	"Pickupo Rental vehicle from Office or Airport| Pick Up Rental SUV |
Options or similar category
* Dacia Duster
included
✅ Automatic
Not included : Safety deposit "
	Day 1	Activity		09/07/2026					Bluelagoon	"Blue Lagoon Premium  Entry ticktes
Included:
Access to the Blue Lagoon
Use of towel
Use of bathrobe
One drink of choice at the in-water bar"
	Day 1	Hotel	1	09/07/2026	10/07/2026				Reykjavik	4 Star ,Hotel Reykjavík Grand , 1x Atrium View Double room ,full double bed, Incl Breakfast
	Day 7	Activity		15/07/2026					Reykjavik	"Reykjavík: Whale Watching From Downtown |
Pick up / meeting point : Old Harbour House, Ægisgarður 2, Reykjavík
What's included?
Pick-up/drop off in central of Reykjavík
Professional, English-speaking guide
Duration 2.5 -3.5h with panoramic views
Warm blankets & restroom on board
Please check-in 30 minutes before departure. Pick-up service is 75–45 minutes before departure."
"""
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    grouped = group_rows_by_day(rows)
    assert_equal(create_trip_title(rows, grouped), "Iceland Summer Escape", "Iceland-only itineraries should not be branded Nordic.")
    assert_contains(create_destinations_line(rows), "Reykjavík", "Overnight stays should drive the route line.")
    assert_not_contains(create_destinations_line(rows), "Blue Lagoon", "Day-trip spa locations should not enter the main overnight route.")
    glance = create_trip_glance(rows, grouped)
    assert_contains(glance["Travel Style"], "self-drive", "Rental vehicle rows should create a self-drive travel style.")
    blue = next(row for row in rows if row.get("city") == "Blue Lagoon")
    assert_equal(create_client_activity_title(blue), "Blue Lagoon Admission", "Admission products should not become guided experiences.")
    whale = next(row for row in rows if "Whale" in row.get("title", ""))
    assert_equal(whale.get("duration"), "2.5–3.5 hours", "Activity duration should beat pick-up-window timing.")
    assert_not_contains(get_activity_description(whale), "Ranua", "Fallback descriptions must not leak unrelated itinerary content.")


def test_real_input_fixture_bank_core_expectations():
    from generator import create_trip_title, create_trip_glance, create_destinations_line
    from itinerary_generation.titles import create_client_activity_title
    from ui.day_blocks import build_day_overview_block

    fixtures = Path(__file__).resolve().parent / "fixtures" / "real_inputs"
    expectations = {
        "iceland_self_drive_summer.txt": {
            "title": "Iceland Summer Escape",
            "route_contains": ["Reykjavík", "Öræfi"],
            "style_contains": "self-drive",
            "forbidden": ["Nordic Summer Journey", "Bluelagoon", "National Park National Park", "Ranua"],
        },
        "norway_sweden_denmark_summer.txt": {
            "title": "Scandinavian Summer Discovery",
            "route_contains": ["Oslo", "Stockholm", "Copenhagen"],
            "forbidden": ["Nordic Summer Journey"],
        },
        "finland_norway_winter_variant.txt": {
            "title": "Lapland & Norway Northern Lights Escape",
            "route_contains": ["Helsinki", "Rovaniemi", "Bergen", "Oslo"],
        },
        "scandinavia_autumn_cruise.txt": {
            "title": "Scandinavian Coastal Voyage",
            "route_contains": ["Copenhagen", "Stockholm", "Kirkenes", "Bergen", "Oslo"],
        },
        "finland_norway_winter_family.txt": {
            "title": "Lapland & Norway Northern Lights Escape",
            "route_contains": ["Helsinki", "Rovaniemi", "Tromsø"],
        },
    }

    for filename, expected in expectations.items():
        raw = (fixtures / filename).read_text(encoding="utf-8")
        rows = normalize_itinerary_rows(parse_itinerary(raw))
        grouped = group_rows_by_day(rows)
        title = create_trip_title(rows, grouped)
        route = create_destinations_line(rows)
        glance = create_trip_glance(rows, grouped)
        combined = "\n".join(
            [title, route, str(glance)]
            + [str(row.get(key, "")) for row in rows for key in ["city", "title", "details", "duration", "hotel_name", "room_category"]]
        )
        assert_equal(title, expected["title"], f"Unexpected trip title for {filename}.")
        for destination in expected.get("route_contains", []):
            assert_contains(route, destination, f"Route should include {destination} for {filename}.")
        if expected.get("style_contains"):
            assert_contains(glance.get("Travel Style", ""), expected["style_contains"], f"Travel style mismatch for {filename}.")
        for forbidden in expected.get("forbidden", []):
            assert_not_contains(combined, forbidden, f"Forbidden text leaked for {filename}.")

    iceland_rows = normalize_itinerary_rows(parse_itinerary((fixtures / "iceland_self_drive_summer.txt").read_text(encoding="utf-8")))
    blue = next(row for row in iceland_rows if row.get("city") == "Blue Lagoon")
    assert_equal(create_client_activity_title(blue), "Blue Lagoon Admission", "Blue Lagoon should render as admission, not generic guided experience.")
    blue_includes = "\n".join(blue.get("includes", []))
    assert_contains(blue_includes, "Unlimited use of steam bath, sauna, and cold lagoon", "Spa comma inclusions should stay together.")
    whale = next(row for row in iceland_rows if "Whale" in row.get("title", ""))
    assert_equal(whale.get("duration"), "2.5–3.5 hours", "Whale watching duration range should be preserved.")
    fosshotel = next(row for row in iceland_rows if "Fosshotel" in row.get("hotel_name", ""))
    assert_equal(fosshotel.get("room_category"), "1 x Standard Room - Triple", "Hotel parser should preserve room quantity while splitting hotel names before room markers.")

    rental_row = next(row for row in iceland_rows if row.get("effective_type") == "Day Overview" and "Rental" in row.get("details", ""))
    rental_html = build_day_overview_block(rental_row)["html"]
    assert_contains(rental_html, "Rental vehicle", "Rental fixture should use the rental vehicle section.")
    assert_contains(rental_html, "full insurance", "Rental included details should be summarized.")
    assert_not_contains(rental_html, "<li>included</li>", "Included should not be a raw rental bullet.")

    explore_row = next(row for row in iceland_rows if row.get("effective_type") == "Day Overview" and "lava fields" in row.get("details", ""))
    explore_html = build_day_overview_block(explore_row)["html"]
    assert_contains(explore_html, "Explore at your own pace", "Explore fixture should not use Suggested Route.")
    assert_not_contains(explore_html, "Suggested Route", "Explore fixture should not use route label.")


def test_sweden_lapland_supplier_booking_information_not_in_client_inclusions():
    from app_modules.itinerary_render_context import build_itinerary_render_context
    from itinerary_generation.quality_gate import evaluate_client_output_quality, render_document_text

    fixture = Path(__file__).resolve().parent / "fixtures" / "real_inputs" / "sweden_lapland_latest_uploaded.txt"
    rows = normalize_itinerary_rows(parse_itinerary(fixture.read_text(encoding="utf-8")))
    grouped = group_rows_by_day(rows)

    context = build_itinerary_render_context(rows, grouped, {})
    report = evaluate_client_output_quality(context.render_document)
    output_text = render_document_text(context.render_document)

    assert not report.is_blocked
    assert_not_contains(output_text, "Booking Information", "Supplier booking headings must not reach client output.")
    assert_not_contains(output_text, "diet restrictions", "Supplier dietary/admin instructions must not be treated as inclusions.")
    assert_not_contains(output_text, "booking flow", "Supplier booking-flow instructions must not reach final inclusions.")

    included_text = "\n".join(
        item
        for section in context.render_document.final_sections
        if section.title == "What’s included"
        for page in section.pages
        for render_section in page.sections
        if render_section.title == "Activities & experiences"
        for item in render_section.items
    )
    assert_contains(included_text, "Mountain Hike in Abisko", "The real activity should remain included.")
    assert_contains(included_text, "Lunch, coffee and something sweet", "Useful food inclusion should remain.")
    assert_contains(included_text, "Transfer with chair lift to Nuolja Mountain", "Useful transfer/lift inclusion should remain.")
    assert_not_contains(included_text, "we gather at", "Truncated supplier instruction fragments must not remain in inclusions.")


def test_v36c53_optional_arc_transfer_quality_gate():
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
    assert_equal(optional_title, "Whale Watching & Arctic Wildlife Safari", "Optional whale/RIB add-ons should keep their specific title.")
    assert "Day 9" in grouped, "The main Day 9 should remain after optional add-ons are excluded from grouped days."
    day9_titles = "\n".join(row.get("title", "") for row in grouped["Day 9"])
    assert_not_contains(day9_titles, "Optional Addon", "Optional add-ons must not appear as normal included day activities.")
    assert_not_contains(day9_titles, "Whale Watching", "Optional whale watching must not become the main day title.")

    inclusions = "\n".join(item for sec in create_categorized_inclusions(rows, grouped) for item in sec.get("items", []))
    assert_not_contains(inclusions, "Whale Watching & Arctic Wildlife Safari", "Optional add-ons must not appear in normal inclusions.")
    assert_not_contains(inclusions, "Whale Watching From Downtown", "Generic whale title should not leak for the optional Alta RIB safari.")
    assert_contains(inclusions, "Northern Lights Experience", "The included Alta northern lights activity should remain included.")

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


def test_v36c55_clear_transport_wording_system():
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


def test_v36c57_real_uploaded_inputs_quality_gate():
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


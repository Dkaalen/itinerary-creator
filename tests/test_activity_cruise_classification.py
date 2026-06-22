from generator import group_rows_by_day
from itinerary_generation.content_validator import compact_html
from itinerary_generation.day_text import create_day_intro
from itinerary_generation.inclusion_sections import create_categorized_inclusions
from itinerary_generation.row_filters import get_row_type
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from ui.day_blocks import build_day_blocks


ICEBREAKER_DAY_INPUT = """
	Day 4	Arrival	26/12/2026							Rovaniemi	Private Station to Hotel
	Day 4	Hotel	26/12/2026	28/12/2026						Rovaniemi	4 Star, Arctic City Hotel. 2xNight, 1xStandard Double or Twin Room, Incl Brekafast
	Day 4	Activity	26/12/2026							Rovaniemi	"Finnish Arctic Explorer Icebreaker Cruise |Pickup 11:10 AM from Rovaneimi | Drop 17:30 Rovaniemi
Cruise TIme : 13:15 - 15:45 Swedish / 14:15 - 16:45 | pickup and drop from city centre

ExplorerThe classic icebreaker experience. Float in icy Arctic waters, walk on the frozen sea and earn your cruise certificate.Swimming in survival suitsWalk on the frozen seaComplimentary hot drinkCruise & Swim certificateShuttle bus from Rovaniem"
"""


def _normalized_day_4():
    rows = normalize_itinerary_rows(parse_itinerary(ICEBREAKER_DAY_INPUT))
    return rows, group_rows_by_day(rows)["Day 4"]


def test_icebreaker_cruise_activity_does_not_become_travel_arrangement():
    rows, day_rows = _normalized_day_4()
    icebreaker = next(row for row in rows if "Icebreaker" in row.get("title", ""))

    assert icebreaker["effective_type"] == "Activity"

    day_html = "\n".join(block["html"] for block in build_day_blocks(day_rows) if block)
    plain = compact_html(day_html)

    assert "Afternoon Experience" in plain
    assert "Finnish Arctic Explorer Icebreaker Cruise" in plain
    assert "Pick-up 11:10 AM from Rovaniemi; drop-off 5:30 PM in Rovaniemi" in plain
    assert "Floating in icy Arctic waters in survival suits" in plain
    assert "Walk on the frozen sea" in plain
    assert "Cruise & Swim certificate" in plain
    assert "Travel Arrangements Coastal Cruise to Rovaniemi" not in plain
    assert "Coastal Cruise to Rovaniemi" not in plain


def test_arrival_day_intro_does_not_claim_free_time_when_activity_is_booked():
    _, day_rows = _normalized_day_4()

    intro = create_day_intro(day_rows, detail_level="Rich descriptive")

    assert "Welcome to Rovaniemi" in intro
    assert "Icebreaker Cruise" in intro
    assert "rest of the day is yours" not in intro


def test_icebreaker_inclusions_are_activity_inclusions_not_ferry_transport():
    rows, grouped = _normalized_day_4()
    sections = create_categorized_inclusions(rows, {"Day 4": grouped})
    section_text = "\n".join(
        section["title"] + "\n" + "\n".join(section.get("items", []))
        for section in sections
    )

    assert "Activities & experiences" in section_text
    assert "Finnish Arctic Explorer Icebreaker Cruise - 26th of December" in section_text
    assert "Floating in icy Arctic waters in survival suits" in section_text
    assert "Walk on the frozen sea" in section_text
    assert "Cruise & Swim certificate" in section_text
    assert "Ferries & cruises" not in section_text
    assert "Coastal Cruise to Rovaniemi" not in section_text
    assert "ExplorerThe" not in section_text
    assert "suitsWalk" not in section_text
    assert "drinkCruise" not in section_text


def test_fjord_cruise_to_destination_stays_activity_not_cruise_transfer():
    rows = normalize_itinerary_rows(parse_itinerary("""
Day 1	Activity	01.01.2027		Bergen: Fjord cruise to Mostraumen - Duration: 3.5 hr
Day 2	Activity	02.01.2027		Bergen to Mostraumen Fjord Cruise Day Trip 3-4 Hrs
Day 3	Activity	03.01.2027		Bergen: Sightseeing cruise to Mostraumen - Time: 10:00 am - Duration: 3.5 hr
"""))

    assert [get_row_type(row) for row in rows] == ["Activity", "Activity", "Activity"]
    assert all(row["title"] == "Mostraumen Fjord Cruise" for row in rows)

    day_html = compact_html("\n".join(block["html"] for block in build_day_blocks(rows) if block))
    assert "Featured experience Mostraumen Fjord Cruise" in day_html
    assert "Travel Arrangements Coastal Cruise to Mostraumen" not in day_html


def test_standalone_naeroyfjord_sightseeing_cruise_is_not_nutshell_transport():
    rows = normalize_itinerary_rows(parse_itinerary("""
Day 1	Activity	01.01.2027		Flåm: Nærøyfjord sightseeing cruise - Time: 10:00 am - Duration: 2 hr
"""))
    row = rows[0]

    assert get_row_type(row) == "Activity"
    assert row["title"] == "Nærøyfjord Sightseeing Cruise"
    assert row.get("activity_product", {}).get("product_type") == "fjord_cruise"

    day_html = compact_html("\n".join(block["html"] for block in build_day_blocks(rows) if block))
    assert "Nærøyfjord Sightseeing Cruise" in day_html
    assert "Norway in a Nutshell" not in day_html


def test_overnight_and_route_package_cruises_still_remain_transport():
    rows = normalize_itinerary_rows(parse_itinerary("""
Day 1	Activity	01.01.2027		Overnight cruise from Stockholm to Helsinki - Time: 5:00 pm - 10:00 am
Day 2	Activity	02.01.2027		Bergen to Oslo: Day Tour incl. the Flåm Train, Nærøyfjord Cruise & Luggage Transfer - Time: 08:00 am - 08:00 pm - Meeting point: Bergen Central Station - Includes: E-tickets for fjord cruise: Gudvangen to Flåm, E-tickets for Flåm railway: Flåm to Myrdal, E-tickets for Bergen railway: Myrdal to Oslo, Luggage transfer
"""))

    assert get_row_type(rows[0]) == "Cruise"
    assert get_row_type(rows[1]) == "Train"
    assert rows[1]["title"] == "Norway in a Nutshell from Bergen to Oslo"

from generator import group_rows_by_day
from itinerary_generation.content_validator import compact_html, validate_html
from itinerary_generation.structured_builder import build_itinerary_document
from itinerary_generation.transport_domain.parser import standardize_private_transfer_title
from itinerary_generation.transport_domain.titles import get_transport_route_phrase
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from parser_modules.extractors import extract_includes_from_description, extract_meeting_point_from_description
from parser_modules.text_cleanup import fix_common_text, repair_supplier_section_boundaries
from ui.day_blocks import build_day_blocks


def _rows(raw: str):
    return normalize_itinerary_rows(parse_itinerary(raw))


def _day_text(rows, day: str) -> str:
    grouped = group_rows_by_day(rows)
    return compact_html("\n".join(block["html"] for block in build_day_blocks(grouped[day]) if block))


def test_run_on_supplier_sections_are_repaired_before_extraction():
    source = (
        "Copenhagen: City Walking & Canal Tour incl. Change of Guards | 09:00 | 3 Hrs "
        "Pick up / meeting point : Copenhagen Central Station, KøbenhavnOverviewSee Copenhagen’s top sights."
        "What's included?Walking tour by born-and-raised hostPersonalized, small-group experience"
        "Harbor ferry ride through the canalsChange of guards at the royal palaceWhat to expect?See Copenhagen."
    )
    repaired = repair_supplier_section_boundaries(source)

    assert "København\nOverview" in repaired
    assert "What's included?\nWalking tour" in repaired
    assert "host\nPersonalized" in repaired

    cleaned = fix_common_text(repaired)

    assert extract_meeting_point_from_description(cleaned) == "Copenhagen Central Station, Copenhagen"
    assert extract_includes_from_description(cleaned) == [
        "Walking tour by born-and-raised host",
        "Personalized, small-group experience",
        "Harbor ferry ride through the canals",
        "Change of guards at the royal palace",
    ]


def test_multiday_group_tour_day_titles_are_preserved_and_not_collapsed_to_single_ticket_products():
    raw = """
Day 6	Activity	06/10/2026								Laugarbakki	"Day 5: Experience Whales, Viking History, and Coastal Legends

Start your day with a delicious breakfast before exploring Akureyri. Take a leisurely walk to the harbor and embark on a thrilling Whale Watching Tour.
After the whale watching adventure, drive to Glaumbær, Borgarvirki, Hvítserkur and Kolugljúfur. Finally, drive to the hotel in Laugarbakki."
Day 7	Activity	07/10/2026								Reykjavik	"Day 6: Hike Craters, See Waterfalls & Relax at Blue Lagoon

Drive to Grábrók, Glanni waterfall, Hraunfossar, Sturlureykir and Deildartunguhver. Upon returning back to Reykjavík, you will hop on a bus to the Blue Lagoon."
"""
    rows = _rows(raw)
    day_6 = _day_text(rows, "Day 6")
    day_7 = _day_text(rows, "Day 7")

    assert "Experience Whales, Viking History, and Coastal Legends" in day_6
    assert "Featured experience Whale Watching" not in day_6
    assert "embark on a thrilling Whale Watching Tour" in day_6
    assert rows[0]["group_tour_role"] == "day_segment"
    assert "group_tour_package_master_missing" in rows[0]["group_tour_day"]["warnings"]

    assert "Hike Craters, See Waterfalls" in day_7
    assert "Featured experience Blue Lagoon Admission" not in day_7
    assert "Grábrók" in day_7
    assert "Hraunfossar" in day_7


def test_cruise_ferry_and_train_route_direction_uses_supplier_route_not_row_city():
    raw = """
Day 1	Transfer 	21/07/2026	22/07/2026						Stockholm	Overnight Cruise Stockholm to Tallin | 1xsleeper cabin | 05:30 PM to next day arrival 11AM
Day 2	Transfer 	22/07/2026							Helsinki	Tallin to Helisnki 2 Hr cruise
Day 3	Transfer 	23/07/2026	24/07/2026						Stockholm	Overnight cruise Helsinki to Stockholm | 4:45 PM to arrivak next day 10 am
Day 4	Transfer 	17/07/2026							Copenhagen	Oslo to Copenhagen Train 6-7 Hr duration
"""
    rows = _rows(raw)
    route_lines = [get_transport_route_phrase(row) for row in rows]

    assert "Overnight Coastal Cruise from Stockholm to Tallinn" in route_lines
    assert "Coastal Cruise from Tallinn to Helsinki" in route_lines
    assert "Overnight Coastal Cruise from Helsinki to Stockholm" in route_lines
    assert "Scenic Train Transfer from Oslo to Copenhagen" in route_lines
    assert all("arrival next day" not in line.lower() for line in route_lines)


def test_blue_lagoon_return_transfer_product_remains_activity_with_clean_inclusions():
    raw = """
Day 8	Activity	22/09/2026							Reykjavik	"Reykjavík: Blue Lagoon Comfort Ticket & Return Transfer |11 AM| 4 hrs

Pick up / meeting point
BSÍ Bus Terminal, Vatnsmýrarvegur 10, Reykjavík

Overview
Benefit from this all-inclusive comfort package which includes bus transfer from Reykjavik to the Blue Lagoon.

What's included?
Bus transfer from Reykjavik to the Blue Lagoon
Bus transfer from the Blue Lagoon to Reykjavik
Depart for Blue Lagoon from 9.00am to 5.00pm
Return to Reykjavik from 1.15pm to 8.15pm
Comfort package admission to the Blue Lagoon
Silica mud mask, towel and free drink of choice

What to expect?
The Blue Lagoon is one of Iceland's most famous tourist attractions."
"""
    rows = _rows(raw)
    row = rows[0]
    text = _day_text(rows, "Day 8")

    assert row["effective_type"] == "Activity"
    assert "Blue Lagoon Admission" in text
    assert "Travel Arrangements" not in text
    assert "Depart for Blue Lagoon" not in text
    assert "Return to Reykjavík from" not in text
    assert "Comfort package admission to the Blue Lagoon" in text


def test_tallinn_day_excursion_stays_activity_even_with_round_trip_ferry_tickets():
    raw = """
Day 2	Activity	11/07/2026							Helsinki 	Excursion to Tallinn - Round Trip Ferry tickets to Tallin - guided tour of Old Town Tallinn walking TOur ( 2-3 Hrs ) - Time: 10:30 am - 07:30 pm Cruise Duration 2 Hr
"""
    rows = _rows(raw)
    text = _day_text(rows, "Day 2")

    assert rows[0]["effective_type"] == "Activity"
    assert "Excursion to Tallinn" in text or "Tallinn" in text
    assert "Ferry Transfer from tickets to Tallinn" not in text


def test_supplier_data_warnings_catch_suspicious_times_and_missing_hotel_names():
    raw = """
Day 1	Hotel	13/07/2026	15/07/2026						Copenhagen	4 Star , 2xNight , 1xStandard Double Room, Incl Brekafast
Day 2	Activity	18/07/2026							Oslo	"Oslo: Fjord Cruise with Silent Electric Ship | 01:30  AM | 2 Hrs | What's included?
Cruise on the Oslo Fjord
English & Norwegian speaking guides
Free tap water and WiFi"
"""
    rows = _rows(raw)
    doc = build_itinerary_document(rows, group_rows_by_day(rows))
    codes = [warning.code for warning in doc.warnings]

    assert "missing_hotel_name" in codes
    assert "suspicious_activity_time" in codes


def test_private_cruise_terminal_transfer_is_client_safe_and_validator_clean():
    assert standardize_private_transfer_title(
        "Private Hotel to Cruise Terminal", "Private Hotel to Cruise Terminal", "Helsinki"
    ) == "Private transfer from your hotel to the cruise terminal"
    assert standardize_private_transfer_title(
        "Private Terminal to Hotel", "Private Cruise Terminal to Hotel", "Stockholm"
    ) == "Private transfer from the cruise terminal to your accommodation"

    raw = """
Day 1	Transfer 	12/07/2026							Helsinki 	Pirvate Hotel to Cruise Terminal
Day 2	Transfer 	13/07/2026							Stockholm	Pirvate Cruise Terminal to Hotel
"""
    rows = _rows(raw)
    html = "\n".join(_day_text(rows, day) for day in group_rows_by_day(rows))
    assert "Private Hotel to Cruise Terminal" not in html
    assert "Private transfer from your hotel to the cruise terminal" in html
    assert validate_html(html) == []

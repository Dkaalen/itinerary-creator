from app_modules.itinerary_html import _balanced_cover_destinations_html
from generator import group_rows_by_day
from itinerary_generation.inclusion_sections import create_categorized_inclusions
from itinerary_generation.row_filters import is_self_arranged
from itinerary_generation.titles import create_destinations_line, create_client_activity_title
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from ui.travel_sequence_blocks import get_travel_sequence_line


def test_self_arranged_flight_typo_stays_out_of_included_flights():
    row = {
        "day": "Day 5",
        "type": "Transfer",
        "effective_type": "Flight",
        "city": "Tromsø",
        "title": "Flight to Tromsø Self Arrnage, CostNot Included",
        "details": "Flight Bergen to Tromsø Self Arrnage, CostNot Included",
        "includes": [],
    }

    assert is_self_arranged(row)
    assert get_travel_sequence_line(row) == "Self-arranged flight to Tromsø (not included)"

    sections = create_categorized_inclusions([row], group_rows_by_day([row]))
    assert all(section["title"] != "Flights" for section in sections)


def test_sightseeing_northern_lights_cruise_remains_activity():
    text = (
        "\tDay 1\tActivity\t\t02/10/2026\t\t\t\t\t\tTromso\t"
        "Tromso : Northern Lights Cruise with Silent Electric Ship (07:00 pm –10:00 pm) "
        "Departure from central Tromsø | 3-hour fjord cruise | Light meal (soup and bread) and water"
    )

    rows = normalize_itinerary_rows(parse_itinerary(text))

    assert rows[0]["effective_type"] == "Activity"
    assert create_client_activity_title(rows[0]) == "Northern Lights Cruise"


def test_cover_route_keeps_return_to_start_destination():
    rows = [
        {"type": "Hotel", "city": "Reykjavik"},
        {"type": "Hotel", "city": "South Coast"},
        {"type": "Hotel", "city": "Vik"},
        {"type": "Hotel", "city": "Akureyri"},
        {"type": "Hotel", "city": "Reykjavik"},
    ]

    assert create_destinations_line(rows) == "Reykjavík · South Coast · Vík · Akureyri · Reykjavík"


def test_long_cover_route_forces_final_pair_to_own_line():
    html = _balanced_cover_destinations_html("Helsinki · Rovaniemi · Kakslauttanen · Ivalo · Tromsø · Bergen · Oslo")

    assert "<br>" in html
    assert '<span class="cover-destination-pair">Bergen&nbsp;·&nbsp;Oslo</span>' in html

from ui.travel_sequence_blocks import get_travel_arrangement_line
from itinerary_generation.inclusion_sections import create_categorized_inclusions


def _rows_from_text(input_text: str):
    return normalize_itinerary_rows(parse_itinerary(input_text))


def _items_for_section(sections, title):
    for section in sections:
        if section["title"] == title:
            return "\n".join(section["items"])
    return ""


def test_dash_separated_coach_route_keeps_origin_and_destination():
    rows = _rows_from_text(
        "\tDay 1\tTransfer \t\t01/06/2026\t\t\t\t\t\tBergen\t"
        "Coach: Bergen - Voss - 09:00 - Tickets Included"
    )

    sections = create_categorized_inclusions(rows, group_rows_by_day(rows))
    coach_items = _items_for_section(sections, "Coach transfers")

    assert "Coach Transfer from Bergen to Voss" in coach_items
    assert "Coach Transfer to Bergen" not in coach_items


def test_dash_separated_ferry_route_keeps_route_and_car_ticket():
    rows = _rows_from_text(
        "\tDay 1\tFerry \t\t01/06/2026\t\t\t\t\t\tLofoten\t"
        "Ferry transfer Moskenes - Bodø - 15:00 - Car ticket included"
    )

    sections = create_categorized_inclusions(rows, group_rows_by_day(rows))
    ferry_items = _items_for_section(sections, "Ferries & cruises")
    day_line = get_travel_arrangement_line(rows[0])

    assert "Ferry Transfer from Moskenes to Bodø" in ferry_items
    assert "Car ticket included" in ferry_items
    assert day_line.startswith("Ferry Transfer from Moskenes to Bodø")


def test_flight_via_point_survives_when_title_and_details_repeat_route():
    rows = _rows_from_text(
        "\tDay 1\tTransfer \t\t01/06/2026\t\t\t\t\t\tOslo\t"
        "Domestic flight from Bergen to Oslo via Stavanger - Luggage included"
    )

    day_line = get_travel_arrangement_line(rows[0])

    assert "Flight from Bergen to Oslo, via Stavanger" in day_line
    assert "via Stavanger, via Stavanger" not in day_line


def test_cruise_quantity_cabin_detail_is_preserved_without_parentheses():
    rows = _rows_from_text(
        "\tDay 1\tCruise \t\t01/06/2026\t\t\t\t\t\tTrondheim\t"
        "Overnight coastal cruise from Bergen to Trondheim - 2 x Outside Cabin - Breakfast included"
    )

    sections = create_categorized_inclusions(rows, group_rows_by_day(rows))
    cruise_items = _items_for_section(sections, "Ferries & cruises")
    day_line = get_travel_arrangement_line(rows[0])

    assert "Overnight Coastal Cruise from Bergen to Trondheim" in cruise_items
    assert "2 x Outside Cabin" in cruise_items
    assert "2 x Outside Cabin" in day_line


def test_checked_bag_included_is_kept_as_flight_detail():
    rows = _rows_from_text(
        "\tDay 1\tFlight \t\t01/06/2026\t\t\t\t\t\tTromso\t"
        "Flight: Oslo to Tromso - 08:00 - 10:00 - 1 checked bag included"
    )

    sections = create_categorized_inclusions(rows, group_rows_by_day(rows))
    flight_items = _items_for_section(sections, "Flights")

    assert "Flight from Oslo to Tromsø" in flight_items
    assert "1 checked luggage included" in flight_items.lower()


def test_standard_premier_train_seats_survive_day_and_inclusions():
    rows = _rows_from_text(
        "\tDay 1\tTrain \t\t01/06/2026\t\t\t\t\t\tParis\t"
        "Eurostar train London to Paris - 09:00 - 12:20 - 2 x Standard Premier seats - train tickets included"
    )

    day_line = get_travel_arrangement_line(rows[0])
    sections = create_categorized_inclusions(rows, group_rows_by_day(rows))
    rail_items = _items_for_section(sections, "Rail journeys")

    assert "Scenic Train Transfer from London to Paris" in rail_items
    assert "2 x Standard Premier seats" in rail_items
    assert "train ticket included" in rail_items.lower()
    assert "2 x Standard Premier seats" in day_line


def test_transfer_typed_route_train_day_heading_uses_clean_destination_title():
    rows = _rows_from_text(
        "\tDay 1\tTransfer \t\t01/06/2026\t\t\t\t\t\tBergen\t"
        "Train: Oslo to Bergen via Myrdal - 08:25 - 15:00 - 2 x standard class seats - train tickets included"
    )

    from itinerary_generation.transport_titles import get_primary_transport_title

    assert get_primary_transport_title(rows) == "Train to Bergen"


def test_sleeper_compartment_detail_is_preserved_for_night_train():
    rows = _rows_from_text(
        "\tDay 1\tTransfer \t\t01/06/2026\t\t\t\t\t\tNarvik\t"
        "Night train Stockholm to Narvik - 2 x private sleeper compartment - breakfast included"
    )

    day_line = get_travel_arrangement_line(rows[0])
    sections = create_categorized_inclusions(rows, group_rows_by_day(rows))
    rail_items = _items_for_section(sections, "Rail journeys")

    assert "Overnight Train Transfer from Stockholm to Narvik" in rail_items
    assert "2 x private sleeper compartment" in rail_items
    assert "2 x private sleeper compartment" in day_line


def test_decimal_time_parentheses_are_removed_from_activity_titles_but_time_survives():
    rows = _rows_from_text(
        "Day 1\tActivity\t19/06/2026\t\t\t\t\t\t\t\tOslo\t"
        "Oslo: 3h Guided Tour of Oslo (afternoon timing) incl. pick-up from hotel, visit to the Royal Palace\n"
        "Day 2\tActivity\t20/06/2026\t\t\t\t\t\t\t\tOslo\t"
        "Oslo: Electric Fjord Cruise (11.00 - 13.00) incl. archipelago island sightings. Free time in Oslo\n"
        "Day 3\tActivity\t23/06/2026\t\t\t\t\t\t\t\tBergen\t"
        "Bergen: Private Day Tour to Hardanger Fjords & Waterfalls: (1.00 - 17.00) incl. visit to Voss\n"
        "Day 4\tActivity\t25/06/2026\t\t\t\t\t\t\t\tSvolvær\t"
        "Svolvær: TrollFjord Cruise by Silent Electric Ship (10.30 - 14.30) incl. Atlantic Ocean sailing from Svolvær to the majestic Trollfjord"
    )

    assert rows[0]["title"] == "Oslo Guided City Tour"
    assert rows[0]["duration"] == "3 hours"
    assert rows[1]["title"] == "Electric Fjord Cruise"
    assert rows[1]["time"] == "11:00 AM - 1:00 PM"
    assert rows[2]["title"] == "Private Day Tour to Hardanger Fjords & Waterfalls"
    assert rows[2]["time"] == "1:00 PM - 5:00 PM"
    assert rows[3]["title"] == "TrollFjord Cruise by Silent Electric Ship"
    assert rows[3]["time"] == "10:30 AM - 2:30 PM"


def test_multi_room_hotel_quantities_from_plural_and_std_fragments_are_preserved():
    rows = _rows_from_text(
        "Day 1\tHotel\t2\t19/06/2026\t21/06/2026\t\t\t\t\t\tOslo\t"
        "Oslo: 4-star Clarion Hotel The Hub, 2x Family rooms, 4x std. double rooms, incl. breakfast\n"
        "Day 2\tHotel\t2\t24/06/2026\t26/06/2026\t\t\t\t\t\tSvolvær\t"
        "Svolvær: 4-star Thon Hotel Lofoten, 2x Family rooms, 4x std. twin rooms (or accessible rooms), incl. breakfast"
    )

    assert rows[0]["hotel_name"] == "Clarion Hotel The Hub"
    assert rows[0]["room_category"] == "2 x Family Room, 4 x Standard Double Room"
    assert rows[1]["hotel_name"] == "Thon Hotel Lofoten"
    assert rows[1]["room_category"] == "2 x Family Room, 4 x Standard Twin Room"


def test_complex_lavvo_activity_is_not_downgraded_to_arctic_route_transfer():
    rows = _rows_from_text(
        "Day 1\tActivity\t15/10/2026\t\t\t\t\t\t\t\tTromso\t"
        "Tromsø/Lyngen Alps: Crystal Lavvo Stay with Northern Lights, Snowshoeing, Meals & Transfers | "
        "Transfers Please meet at the red Arctic Route bus. Overnight stay in private crystal lavvo."
    )

    assert rows[0]["effective_type"] == "Activity"
    assert rows[0]["title"] == "Lyngen Alps Crystal Lavvo Stay"
    assert create_client_activity_title(rows[0]) == "Lyngen Alps Crystal Lavvo Stay"


def test_optional_recommended_rows_are_excluded_from_main_day_grouping():
    rows = _rows_from_text(
        "Day 1\tActivity\t25/06/2026\t\t\t\t\t\t\t\tSvolvaer\t"
        "OPTIONAL/RECOMMENDED Private sightseeing drive in the Lofoten Islands archipelago (14.00 - 19.00) incl. pick-up/drop-off from the hotel"
    )

    assert rows[0]["is_optional"] is True
    assert group_rows_by_day(rows) == {}


def test_cruise_leisure_days_use_clean_client_title():
    rows = _rows_from_text(
        "Day 1\tCruise\t09.10.2026\t\t\t\t\t\t\t\tCruise\tCruise: Spend time at leisure"
    )

    plan = next(iter(group_rows_by_day(rows).values()))
    from itinerary_generation.day_planner import plan_day

    assert plan_day(plan).title == "At Leisure Onboard the Coastal Cruise"


def test_arrival_city_hotel_to_airport_typo_is_corrected_after_inbound_flight():
    rows = _rows_from_text(
        "Day 1\tTransfer\t26/06/2026\t\t\t\t\t\t\t\tSvolvær\tPrivate Hotel to Airport\n"
        "Day 1\tFlight\t26/06/2026\t\t\t\t\t\t\t\tCopenhagen\tFlight Svolvaer to Copenhagen | Self arranged | cost not included\n"
        "Day 1\tTransfer\t26/06/2026\t\t\t\t\t\t\t\tCopenhagen\tCopenhagen: Private transfer from hotel to airport by Mercedes Benz Sprinter vehicle\n"
        "Day 1\tHotel\t3\t26/06/2026\t29/06/2026\t\t\t\t\t\tCopenhagen\t4Star ,Hotel Mayfair, 3xNight , Standard Doubel Room, Incl Brekafast"
    )

    copenhagen_transfer = [row for row in rows if row.get("city") == "Copenhagen" and row.get("type") == "Transfer"][0]
    assert copenhagen_transfer["title"] == "Private transfer from Copenhagen Airport to your accommodation"

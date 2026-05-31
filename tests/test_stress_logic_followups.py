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
        {"type": "Activity", "city": "South Coast"},
        {"type": "Activity", "city": "Vik"},
        {"type": "Activity", "city": "Akureyri"},
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

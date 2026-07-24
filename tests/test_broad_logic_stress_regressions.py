from tests.support.inclusion_contract import (
    build_inclusion_sections,
    inclusion_item_text,
    inclusion_item_texts,
    inclusion_section_text,
    inclusion_text,
)
from generator import group_rows_by_day
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from itinerary_generation.inclusions import create_whats_included
from ui.travel_sequence_blocks import get_travel_arrangement_line


def _rows(input_text: str):
    return normalize_itinerary_rows(parse_itinerary(input_text))


def _section_items(sections, title):
    for section in sections:
        if section.title == title:
            return inclusion_item_texts(section)
    return []


def test_daytime_train_preserves_seat_quantity_without_raw_supplier_title():
    rows = _rows(
        "\tDay 1\tTransfer \t\t01/06/2026\t\t\t\t\t\tOslo\t"
        "Train: Oslo to Bergen - 08:25 - 15:00 - 2 x standard class seats - tickets included"
    )

    sections = build_inclusion_sections(rows, group_rows_by_day(rows))
    rail_items = "\n".join(_section_items(sections, "Rail journeys"))

    assert "Scenic Train Transfer from Oslo to Bergen" in rail_items
    assert "2 x standard class seats" in rail_items
    assert "train ticket included" in rail_items.lower()
    assert "08:25" not in rail_items


def test_ferry_transfer_keeps_route_and_car_ticket_without_duplicate_generic_ticket():
    rows = _rows(
        "\tDay 1\tTransfer \t\t01/06/2026\t\t\t\t\t\tTromso\t"
        "Ferry: Brensholmen to Botnhamn - 11:00 - 11:45 - Car ticket included"
    )

    sections = build_inclusion_sections(rows, group_rows_by_day(rows))
    ferry_items = "\n".join(_section_items(sections, "Ferries & cruises"))
    day_line = get_travel_arrangement_line(rows[0])

    assert "Ferry Transfer from Brensholmen to Botnhamn" in ferry_items
    assert "Car ticket included" in ferry_items
    assert "Ticket included and car ticket" not in ferry_items
    assert day_line.startswith("Ferry Transfer from Brensholmen to Botnhamn")
    assert "Car ticket included" in day_line or "car ticket included" in day_line


def test_legacy_flat_inclusions_use_hotel_row_nights_not_day_count_only():
    rows = _rows(
        "\tDay 1\tHotel\t1\t01/06/2026\t02/06/2026\t\t\t\t\tOslo\t"
        "4 Star, Hotel Example, 1xNight, 1x Standard Room, Incl Breakfast"
    )

    included = create_whats_included(rows, group_rows_by_day(rows))

    assert "1 night as specified" in included
    assert "0 nights as specified" not in included


def test_night_train_keyword_preserves_overnight_label_and_cabin_quantity():
    rows = _rows(
        "\tDay 1\tTransfer \t\t01/06/2026\t\t\t\t\t\tStockholm\t"
        "Night train: Stockholm to Abisko - 18:10 - 10:55 - 2 x private sleeper cabin for two people - train ticket included"
    )

    sections = build_inclusion_sections(rows, group_rows_by_day(rows))
    rail_items = "\n".join(_section_items(sections, "Rail journeys"))
    day_line = get_travel_arrangement_line(rows[0])

    assert "Overnight Train Transfer from Stockholm to Abisko" in rail_items
    assert "2 x private sleeper cabin for two people" in rail_items
    assert "train ticket included" in rail_items.lower()
    assert day_line.startswith("Overnight Train Transfer from Stockholm to Abisko")
    assert "2 x private sleeper cabin for two people" in day_line


def test_flight_via_point_is_not_duplicated_in_route_phrase():
    rows = _rows(
        "\tDay 1\tFlight \t\t01/06/2026\t\t\t\t\t\tOslo\t"
        "Flight: Tromsø to Oslo via Bodø - 12:10 - 15:45 - Luggage included"
    )

    day_line = get_travel_arrangement_line(rows[0])

    assert "Flight from Tromsø to Oslo, via Bodø" in day_line
    assert "via Bodø, via Bodø" not in day_line


def test_transfer_row_coach_day_line_keeps_clean_destination_without_ticket_noise():
    rows = _rows(
        "\tDay 1\tTransfer \t\t01/06/2026\t\t\t\t\t\tSaariselka\t"
        "Bus :Long distance comfortable panorama coach transfer from Saariselka t to Rovaniemi Bus Station  - Tickets Included"
    )

    day_line = get_travel_arrangement_line(rows[0])

    assert day_line.startswith("Coach Transfer to Rovaniemi Bus Station")
    assert "Rovaniemi bus Station" not in day_line
    assert "Tickets Included" not in day_line


def test_cruise_cabin_and_meal_in_title_are_kept_as_details():
    rows = _rows(
        "\tDay 1\tCruise \t\t01/06/2026\t\t\t\t\t\tOslo\t"
        "Overnight cruise from Copenhagen to Oslo onboard DFDS Crown - Cabin (Seaview) - Dinner included"
    )

    sections = build_inclusion_sections(rows, group_rows_by_day(rows))
    cruise_items = "\n".join(_section_items(sections, "Ferries & cruises"))
    day_line = get_travel_arrangement_line(rows[0])

    assert "Overnight Coastal Cruise from Copenhagen to Oslo onboard DFDS Crown" in cruise_items
    assert "Seaview cabin" in cruise_items
    assert "dinner included" in cruise_items.lower()
    assert "Seaview cabin" in day_line

from tests.support.inclusion_contract import (
    build_inclusion_sections,
    inclusion_item_text,
    inclusion_item_texts,
    inclusion_section_text,
    inclusion_text,
)
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from itinerary_generation.common import group_rows_by_day
from itinerary_generation.transport_routes import get_route_points_for_transport
from itinerary_generation.transport_titles import get_transport_route_phrase, get_primary_transport_title
from ui.travel_sequence_blocks import get_travel_arrangement_line


def _sections_text(rows):
    sections = build_inclusion_sections(rows, group_rows_by_day(rows))
    return "\n".join(item for section in sections for item in inclusion_item_texts(section))


def test_finland_overnight_trains_keep_direction_and_cabins_in_days_and_inclusions():
    raw = """
\tDay 2\tTransfer \t\t15/11/2026\t\t\t\t\t\tHelsinki \tOvernight Train : Overnight Train Transfer with the Santa Claus Express to Rovaniemi - 11:13 pm - 10:59 am - 4  x  downstairs cabin for two people
\tDay 3\tHotel\t2\t16/11/2026\t18/11/2026\t\t\t\t\tRovaniemi\t4 Star, Original Sokos Hotel Vaakuna Rovaniemi , 2xNight , 3xStandard  Room, Incl Brekafast
\tDay 6\tTransfer \t\t19/11/2026\t\t\t\t\t\tRovaniemi\tOvernight Train : Overnight Train Transfer with the Santa Claus Express to Helsinki - 21:00 pm - 09:00 am - 4  x  downstairs cabin for two people
\tDay 7\tDeparture\t\t20/11/2026\t\t\t\t\t\tHelsinki \tDeparture
"""
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    trains = [row for row in rows if row.get("effective_type") == "Train"]

    assert [row["title"] for row in trains] == ["Overnight Train to Rovaniemi", "Overnight Train to Helsinki"]
    assert "4 x downstairs cabin for two people" in get_travel_arrangement_line(trains[0])
    assert "4 x downstairs cabin for two people" in get_travel_arrangement_line(trains[1])
    assert get_primary_transport_title([trains[1]]) == "Santa Claus Express to Helsinki"

    inclusions = _sections_text(rows)
    assert "Santa Claus Express to Rovaniemi" in inclusions
    assert "Santa Claus Express to Helsinki" in inclusions
    assert inclusions.count("4 x downstairs cabin for two people") == 2


def test_return_coach_transfer_preserves_reverse_route_with_bus_station():
    raw = """
\tDay 5\tTransfer \t\t18/11/2026\t\t\t\t\t\tSaariselka\tBus : Long distance comfortable panorama coach transfer from Rovaniemi Bus Station to Saariselka  - Tickets Included
\tDay 6\tTransfer \t\t19/11/2026\t\t\t\t\t\tSaariselka\tBus :Long distance comfortable panorama coach transfer from Saariselka t to Rovaniemi Bus Station  - Tickets Included
"""
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    first, second = rows

    assert get_route_points_for_transport(second) == ("Saariselkä", "Rovaniemi Bus Station")
    assert get_transport_route_phrase(first) == "Panoramic Coach Transfer from Rovaniemi Bus Station to Saariselkä"
    assert get_transport_route_phrase(second) == "Panoramic Coach Transfer from Saariselkä to Rovaniemi Bus Station"

    inclusions = _sections_text(rows)
    assert "Panoramic Coach Transfer from Rovaniemi Bus Station to Saariselkä" in inclusions
    assert "Panoramic Coach Transfer from Saariselkä to Rovaniemi Bus Station" in inclusions


def test_accommodation_quantities_survive_normalization_and_inclusions():
    raw = """
\tDay 3\tHotel\t2\t16/11/2026\t18/11/2026\t\t\t\t\tRovaniemi\t3 Star , Hotel Aakenus  2xNight , 3x Tirple Room, Incl Brekafast
\tDay 5\tHotel\t1\t18/11/2026\t19/11/2026\t\t\t\t\tSaariselka\t4 Star , Northern Light Village Sariselka  , 1xNight ,  3xPanorama Suite  , Incl Breakfast + Dinner
"""
    rows = normalize_itinerary_rows(parse_itinerary(raw))

    assert rows[0]["room_category"] == "3 x Triple Room"
    assert rows[1]["room_category"] == "3 x Panorama Suite"

    inclusions = _sections_text(rows)
    assert "3 x Triple Room" in inclusions
    assert "3 x Panorama Suite" in inclusions


def test_train_cabin_detail_does_not_absorb_repeated_supplier_title():
    raw = """
\tDay 6\tTransfer \t1\t19/11/2026\t20/11/2026\t\t\t\t\tRovaniemi\tOvernight Train : Overnight Train Transfer with the Santa Claus Express to Helsinki - 21:00 pm - 09:00 am - 4  x  downstairs cabin for two people
"""
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    train = rows[0]

    assert "4 x downstairs cabin for two people" in get_travel_arrangement_line(train)
    assert "Overnight Train:" not in get_travel_arrangement_line(train).split(";", 1)[-1]

    inclusions = _sections_text(rows)
    assert "4 x downstairs cabin for two people." in inclusions
    assert "for two people Overnight Train" not in inclusions


def test_journey_arc_hotel_meal_plan_does_not_invent_food_culture():
    from itinerary_generation.summaries import create_journey_arc

    raw = """
\tDay 5\tTransfer \t\t18/11/2026\t\t\t\t\t\tSaariselka\tBus : Long distance comfortable panorama coach transfer from Rovaniemi Bus Station to Saariselka  - Tickets Included
\tDay 5\tHotel\t1\t18/11/2026\t19/11/2026\t\t\t\t\tSaariselka\t4 Star , Northern Light Village Sariselka  , 1xNight ,  3xPanorama Suite  , Incl Breakfast + Dinner
"""
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    arc = create_journey_arc(group_rows_by_day(rows))

    assert arc[0]["experience"] == "Northern Lights village stay"
    assert "food culture" not in arc[0]["experience"].lower()

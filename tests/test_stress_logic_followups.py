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

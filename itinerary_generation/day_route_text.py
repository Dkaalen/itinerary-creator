"""Route-label helpers for travel-only day intro text."""

from __future__ import annotations

from itinerary_generation.common_constants import TRANSPORT_TYPES
from itinerary_generation.row_filters import get_row_type
from itinerary_generation.transport_domain.route_cleaning import canonical_route_city
from itinerary_generation.transport import get_transfer_travel_title, is_route_transfer



# Compatibility alias; route spelling is owned by the transport domain.
_canonical_route_city = canonical_route_city

ROUTE_CITY_CANDIDATES = [
    "Helsinki", "Rovaniemi", "Saariselkä", "Saariselka",
    "Kakslauttanen", "Kakslauttenen", "Ivalo",
    "Oslo", "Bergen", "Copenhagen", "Stockholm", "Tromsø", "Tromso", "Svolvær", "Svolvaer", "Svolaver", "Gothenburg", "Göteborg", "Malmo", "Malmø", "Alta", "Kirkenes",
]


def _ordered_route_cities(day_rows):
    cities = []

    def add_city(city):
        city = _canonical_route_city(city)
        if city and city.lower() not in [existing.lower() for existing in cities]:
            cities.append(city)

    for row in day_rows:
        if get_row_type(row) not in TRANSPORT_TYPES and get_row_type(row) != "Transfer" and not is_route_transfer(row):
            continue
        add_city(row.get("city", ""))
        row_text = get_transfer_travel_title(row) if is_route_transfer(row) else f'{row.get("title", "")} {row.get("details", "")}'
        for possible_city in ROUTE_CITY_CANDIDATES:
            if possible_city.lower() in row_text.lower():
                add_city(possible_city)
    return cities


def create_travel_route_label(day_rows):
    """Return a natural route label for travel-only days, when clear enough."""

    has_activity_or_hotel = any(get_row_type(row) in {"Activity", "Hotel"} for row in day_rows)
    if has_activity_or_hotel:
        return ""

    travel_rows = [row for row in day_rows if get_row_type(row) in TRANSPORT_TYPES or get_row_type(row) == "Transfer" or is_route_transfer(row)]
    if len(travel_rows) < 2:
        return ""

    cities = _ordered_route_cities(day_rows)
    if len(cities) < 3:
        return ""

    has_overnight_final_leg = any(
        "overnight" in f'{row.get("title", "")} {row.get("details", "")}'.lower()
        for row in travel_rows[-1:]
    )
    if has_overnight_final_leg:
        return f"{cities[0]} to {cities[-2]}, overnight to {cities[-1]}"

    return f"{cities[0]} to {cities[-1]}"



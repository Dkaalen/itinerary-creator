"""Destination city validation and summary helpers."""

from __future__ import annotations

import re

from place_aliases import canonicalize_place_name, country_for_place, is_likely_service_text
from itinerary_generation.common_constants import TRANSPORT_TYPES
from itinerary_generation.row_filters import get_row_type, is_optional_row


def is_valid_destination_city(city):
    city = canonicalize_place_name(str(city or "").strip())
    if not city:
        return False
    lower = city.lower()
    invalid_markers = [
        "private hotel",
        "private airport",
        "hotel to airport",
        "airport to hotel",
        "optional addon",
        "optional add",
        "optinal addon",
        "addon on request",
        "flight ",
    ]
    invalid_exact = {"accommodation", "hotel", "train", "flight", "cruise", "departure", "arrival", "car", "drive", "self drive", "self-drive"}
    if lower in invalid_exact:
        return False
    if any(re.search(pattern, lower) for pattern in [r"\bshower\b", r"\bsink\b", r"\bwc in carriage\b", r"\bbenefits\b", r"\bmade bed\b", r"women's", r"men's compartment"]):
        return False
    if is_likely_service_text(city):
        return False
    if any(marker in lower for marker in invalid_markers):
        return False
    if " to " in lower and any(word in lower for word in ["airport", "hotel", "station", "bergen", "copenhagen", "svol"]):
        return False
    return True


def clean_client_title(value):
    """Small client-facing title cleanup used after parsing."""

    title = str(value or "").strip()
    if not title:
        return ""

    # Remove over-marketing phrases that should not appear in polished itineraries.
    cleanup_phrases = [
        "with 97% Success Rate",
        "with Pro Photos Included",
        "with Pro Photographer",
        "with Professional Photographer",
        "Included",
    ]

    for phrase in cleanup_phrases:
        title = title.replace(phrase, "")

    title = title.replace("  ", " ").strip(" -:|")
    return title


def get_display_destination_city(city):
    """Return the client-facing city label used in route/glance summaries.

    Synthetic group-tour accommodation rows sometimes use area labels such as
    "Vík area" or "Höfn area". The cover/glance route should keep the travel
    route clean, so those area suffixes are collapsed to the destination name.
    """
    value = canonicalize_place_name(str(city or "").strip())
    value = re.sub(r"\s+area$", "", value, flags=re.IGNORECASE).strip()
    return value


def _city_from_route_place(place: str) -> str:
    """Collapse station/terminal route points to destination-city labels."""

    value = get_display_destination_city(place)
    if not value:
        return ""

    terminal_clean = re.sub(
        r"\s+(?:bus\s*station|bus\s*terminal|busterminal|busstation|coach\s*station|coach\s*terminal|"
        r"central\s*station|railway\s*station|train\s*station|rail\s*station|station|airport|"
        r"ferry\s*terminal|cruise\s*terminal|terminal|harbou?r|port|pier|dock)\b.*$",
        "",
        value,
        flags=re.IGNORECASE,
    ).strip(" -:|.,")
    if terminal_clean:
        canonical = get_display_destination_city(terminal_clean)
        if canonical and not is_likely_service_text(canonical):
            return canonical
    return value


def destination_cities_for_row(row: dict) -> list[str]:
    """Return city labels represented by one itinerary row.

    Prefer the explicit city cell, but enrich route-only transport rows from
    parsed origin/destination points so cover and trip-glance metadata do not
    fall back to TBA when the route is clearly present in the supplier text.
    """

    cities: list[str] = []

    def add_city(value: object) -> None:
        city = _city_from_route_place(str(value or ""))
        if is_valid_destination_city(city) and city not in cities:
            cities.append(city)

    add_city(row.get("city", ""))

    row_type = get_row_type(row)
    if row_type in set(TRANSPORT_TYPES) | {"Transfer"}:
        # Import lazily: transport route extraction depends on the common facade,
        # which in turn re-exports this destination module. Lazy import keeps the
        # boundary acyclic at module-import time.
        from itinerary_generation.transport_routes import get_route_points_for_transport

        origin, destination = get_route_points_for_transport(row)
        add_city(origin)
        add_city(destination)

    return cities


def get_unique_cities(parsed_rows):
    cities = []

    for row in parsed_rows:
        if is_optional_row(row):
            continue

        for city in destination_cities_for_row(row):
            if city not in cities:
                cities.append(city)

    return cities


def get_destination_countries(parsed_rows):
    """Return unique known countries represented by itinerary destination cities."""
    countries = []
    for city in get_unique_cities(parsed_rows):
        country = country_for_place(city)
        if country and country not in countries:
            countries.append(country)
    return countries


def get_primary_city(day_rows):
    """
    Prefer the city of the main hotel/activity for mixed transfer days.
    This avoids days like Tromsø -> Bergen showing only the departure city.
    """

    if not day_rows:
        return ""

    priority_types = ["Activity", "Hotel", "Flight", "Train", "Transport", "Cruise", "Ferry", "Arrival", "Departure", "Transfer"]

    for preferred_type in priority_types:
        for row in day_rows:
            if get_row_type(row) == preferred_type:
                for city in destination_cities_for_row(row):
                    if city and is_valid_destination_city(city):
                        return city

    for city in destination_cities_for_row(day_rows[0]):
        if city:
            return city
    return canonicalize_place_name(day_rows[0].get("city", "").strip())


def get_row_city(day_rows):
    city = get_primary_city(day_rows)
    return city or "the destination"

"""Travel-signal helpers for day facts."""

from __future__ import annotations

from typing import Any, Mapping

from itinerary_generation.common import TRANSPORT_TYPES, get_row_type
from itinerary_generation.day_city_facts import canonical_city, row_text
from itinerary_generation.transport_detection import is_route_transfer
from itinerary_generation.transport_domain.route_summary import transport_endpoints_from_row

TRAVEL_ROW_TYPES = set(TRANSPORT_TYPES) | {"Transfer", "Transport", "Coach", "Bus", "Drive"}
STATION_WORDS = ("station", "airport", "harbour", "harbor", "port", "terminal", "pier", "dock")
OVERNIGHT_MARKERS = ("overnight", "night train", "sleeper", "sleeping compartment", "night ferry", "night cruise")


def transport_endpoints(row: Mapping[str, Any]) -> tuple[str, str]:
    """Return canonical origin/destination endpoint facts for transport rows."""

    row_type = get_row_type(dict(row))
    if row_type not in TRAVEL_ROW_TYPES:
        return "", ""
    if row_type == "Transfer" and not is_route_transfer(dict(row)):
        return "", ""
    origin, destination = transport_endpoints_from_row(dict(row))
    return canonical_city(origin), canonical_city(destination)


def is_local_transfer(row: Mapping[str, Any], *, accommodation_words: tuple[str, ...]) -> bool:
    """Return whether a row is a local logistics transfer, not route travel."""

    if get_row_type(dict(row)) != "Transfer":
        return False
    text = row_text(row).lower()
    if is_route_transfer(dict(row)):
        return False
    return any(marker in text for marker in (*STATION_WORDS, *accommodation_words, "private transfer", "self transfer"))


__all__ = ["OVERNIGHT_MARKERS", "STATION_WORDS", "TRAVEL_ROW_TYPES", "is_local_transfer", "transport_endpoints"]

"""Transport row detection helpers."""

from __future__ import annotations

from itinerary_generation.common import (
    TRANSPORT_TYPES,
    get_row_type,
    is_self_arranged,
    is_valid_destination_city,
)
from itinerary_generation.transport_routes import _route_destination_from_text


def is_route_transfer(row):
    if get_row_type(row) != "Transfer":
        return False
    text = f'{row.get("title", "")} {row.get("details", "")}'
    lower = text.lower()
    if any(marker in lower for marker in ["private", "shuttle", "self transfer", "hotel to", "airport to", "to hotel", "to airport", "to station", "accommodation"]):
        return False
    destination = _route_destination_from_text(text)
    return bool(destination and is_valid_destination_city(destination))


def has_self_arranged_transport(day_rows):
    return any(get_row_type(row) in TRANSPORT_TYPES and is_self_arranged(row) for row in day_rows)


def has_glass_igloo_or_arctic_resort(rows):
    hotel_text = " ".join(
        f'{row.get("hotel_name", "")} {row.get("room_category", "")} {row.get("details", "")}'
        for row in rows
        if get_row_type(row) == "Hotel"
    ).lower()
    return any(marker in hotel_text for marker in ["glass igloo", "kakslauttanen", "arctic resort"])

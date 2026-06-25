"""Transport row detection helpers."""

from __future__ import annotations

from itinerary_generation.common_constants import TRANSPORT_TYPES
from itinerary_generation.row_filters import get_row_type, is_self_arranged
from itinerary_generation.transport_model import has_local_transfer_marker
from itinerary_generation.transport_domain.routes import _route_destination_from_text, get_route_points_for_transport
from itinerary_generation.transport_safety import base_destination_from_terminal


def is_route_transfer(row):
    if get_row_type(row) != "Transfer":
        return False
    text = f'{row.get("title", "")} {row.get("details", "")}'
    lower = text.lower()
    if has_local_transfer_marker(lower):
        return False
    _, destination = get_route_points_for_transport(row)
    destination = base_destination_from_terminal(destination) or _route_destination_from_text(text)
    if not destination:
        return False
    from itinerary_generation.destination_helpers import is_valid_destination_city

    return is_valid_destination_city(destination)


def has_self_arranged_transport(day_rows):
    return any(get_row_type(row) in TRANSPORT_TYPES and is_self_arranged(row) for row in day_rows)


def has_glass_igloo_or_arctic_resort(rows):
    hotel_text = " ".join(
        f'{row.get("hotel_name", "")} {row.get("room_category", "")} {row.get("details", "")}'
        for row in rows
        if get_row_type(row) == "Hotel"
    ).lower()
    return any(marker in hotel_text for marker in ["glass igloo", "kakslauttanen", "arctic resort"])

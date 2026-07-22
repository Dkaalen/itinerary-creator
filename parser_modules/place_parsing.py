"""Stable parser facade for place values and generic route parsing."""
from __future__ import annotations

from .place_values import (
    INVALID_CITY_MARKERS,
    INVALID_CITY_VALUES,
    is_valid_city_value,
    normalize_place_name,
)
from .route_parsing import (
    _clean_route_destination,
    _clean_route_origin,
    _explicit_transport_route_points,
    _generic_to_route_points,
    _is_rejected_route_destination,
    _named_group_route_points,
    _repair_missed_to,
    _route_source_and_prefix,
    _scheduled_route_points,
    _self_drive_route_points,
    _timed_leg_route_points,
    _valid_route_pair,
    extract_route_points,
)


def city_airport(city):
    city = normalize_place_name(city)
    return f"{city} Airport" if city else "the airport"


__all__ = [
    "INVALID_CITY_MARKERS",
    "INVALID_CITY_VALUES",
    "city_airport",
    "extract_route_points",
    "is_valid_city_value",
    "normalize_place_name",
]

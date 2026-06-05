"""Compatibility facade for canonical transport route helpers."""

from __future__ import annotations

from itinerary_generation.transport_domain.routes import (
    _ROUTE_PREFIX_ORIGINS,
    _clean_route_place,
    _route_destination_from_text,
    _transport_source_text,
    _via_suffix,
    get_route_points_for_transport,
    get_route_via_points,
)

__all__ = [
    "_ROUTE_PREFIX_ORIGINS",
    "_clean_route_place",
    "_route_destination_from_text",
    "_transport_source_text",
    "_via_suffix",
    "get_route_points_for_transport",
    "get_route_via_points",
]

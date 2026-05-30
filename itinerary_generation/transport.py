"""Compatibility facade for itinerary transport helpers."""

from __future__ import annotations

from itinerary_generation.transport_airport import (
    has_airport_arrival_transfer,
    has_airport_departure_transfer,
    has_only_departure_arrangements,
)
from itinerary_generation.transport_detection import (
    has_glass_igloo_or_arctic_resort,
    has_self_arranged_transport,
    is_route_transfer,
)
from itinerary_generation.transport_norway import (
    _is_norway_in_a_nutshell_text,
    _norway_nutshell_route_label,
    has_norway_in_a_nutshell,
)
from itinerary_generation.transport_routes import (
    _ROUTE_PREFIX_ORIGINS,
    _clean_route_place,
    _route_destination_from_text,
    _transport_source_text,
    _via_suffix,
    get_route_points_for_transport,
    get_route_via_points,
)
from itinerary_generation.transport_titles import (
    get_first_transfer_title,
    get_premium_transport_phrase,
    get_primary_transport_title,
    get_transport_route_phrase,
    get_transfer_travel_title,
)

__all__ = [
    "_ROUTE_PREFIX_ORIGINS",
    "_clean_route_place",
    "_is_norway_in_a_nutshell_text",
    "_norway_nutshell_route_label",
    "_route_destination_from_text",
    "_transport_source_text",
    "_via_suffix",
    "get_first_transfer_title",
    "get_premium_transport_phrase",
    "get_primary_transport_title",
    "get_transport_route_phrase",
    "get_route_points_for_transport",
    "get_route_via_points",
    "get_transfer_travel_title",
    "has_airport_arrival_transfer",
    "has_airport_departure_transfer",
    "has_glass_igloo_or_arctic_resort",
    "has_norway_in_a_nutshell",
    "has_only_departure_arrangements",
    "has_self_arranged_transport",
    "is_route_transfer",
]

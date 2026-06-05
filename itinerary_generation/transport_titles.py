"""Compatibility facade for canonical transport title helpers."""

from __future__ import annotations

from itinerary_generation.transport_domain.titles import (
    get_first_transfer_title,
    get_premium_transport_phrase,
    get_primary_transport_title,
    get_transport_route_phrase,
    get_transfer_travel_title,
)

__all__ = [
    "get_first_transfer_title",
    "get_premium_transport_phrase",
    "get_primary_transport_title",
    "get_transport_route_phrase",
    "get_transfer_travel_title",
]

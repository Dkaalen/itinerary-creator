"""Compatibility facade for canonical transport inclusion helpers."""

from __future__ import annotations

from itinerary_generation.transport_domain.inclusions import (
    clean_transport_title,
    is_cruise_arrival_row,
    is_cruise_leisure_row,
    is_self_transfer_row,
    route_transport_line,
    transport_bucket,
    transport_line,
)

__all__ = [
    "clean_transport_title",
    "is_cruise_arrival_row",
    "is_cruise_leisure_row",
    "is_self_transfer_row",
    "route_transport_line",
    "transport_bucket",
    "transport_line",
]

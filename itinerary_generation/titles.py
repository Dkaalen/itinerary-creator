"""Compatibility facade for itinerary title helpers."""

from __future__ import annotations

from itinerary_generation.activity_titles import (
    create_client_activity_title,
    is_bad_raw_day_title,
    normalize_client_day_title,
)
from itinerary_generation.day_titles import create_day_title
from itinerary_generation.title_routes import (
    _extract_supplier_day_heading,
    _looks_like_norway_in_a_nutshell,
    _route_label_from_activity_text,
)
from itinerary_generation.trip_titles import (
    _join_destinations_naturally,
    create_destinations_line,
    create_trip_subtitle,
    create_trip_title,
)

__all__ = [
    "_extract_supplier_day_heading",
    "_join_destinations_naturally",
    "_looks_like_norway_in_a_nutshell",
    "_route_label_from_activity_text",
    "create_client_activity_title",
    "create_day_title",
    "create_destinations_line",
    "create_trip_subtitle",
    "create_trip_title",
    "is_bad_raw_day_title",
    "normalize_client_day_title",
]

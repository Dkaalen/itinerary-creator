"""Compatibility facade for trip-level titles.

Trip Brain owns trip title/subtitle decisions. This module keeps the historical
import path and small formatting helper stable.
"""

from __future__ import annotations

from itinerary_generation.cover_route import create_cover_route_line
from itinerary_generation.trip_brain import create_trip_subtitle_from_brain, create_trip_title_from_brain


def create_trip_title(parsed_rows, grouped_days):
    """Return the Trip Brain itinerary title."""

    return create_trip_title_from_brain(parsed_rows, grouped_days)


def create_trip_subtitle(parsed_rows, grouped_days):
    """Return the Trip Brain itinerary subtitle."""

    return create_trip_subtitle_from_brain(parsed_rows, grouped_days)


def create_destinations_line(parsed_rows):
    """Return the cover-route destination line."""

    return create_cover_route_line(parsed_rows)


def _join_destinations_naturally(cities):
    clean_cities = [str(city or "").strip() for city in cities if str(city or "").strip()]
    if not clean_cities:
        return "the Nordics"
    if len(clean_cities) == 1:
        return clean_cities[0]
    if len(clean_cities) == 2:
        return f"{clean_cities[0]} and {clean_cities[1]}"
    return ", ".join(clean_cities[:-1]) + f" and {clean_cities[-1]}"


__all__ = [
    "_join_destinations_naturally",
    "create_destinations_line",
    "create_trip_subtitle",
    "create_trip_title",
]

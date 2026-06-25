"""Compatibility facade for trip summary helpers."""

from __future__ import annotations

from itinerary_generation.summaries_experience import describe_city_experience
from itinerary_generation.summaries_journey_arc import create_journey_arc, format_day_range
from itinerary_generation.summaries_text import (
    _add_theme,
    _compact_arc_phrase,
    _has,
    _title_case_arc,
    _welcome_arc_phrase,
    sanitize_journey_arc_experience,
)
from itinerary_generation.summaries_trip_glance import create_trip_glance

__all__ = (
    "create_trip_glance",
    "_has",
    "_add_theme",
    "_welcome_arc_phrase",
    "sanitize_journey_arc_experience",
    "_title_case_arc",
    "_compact_arc_phrase",
    "describe_city_experience",
    "format_day_range",
    "create_journey_arc",
)

"""Compatibility facade for itinerary summary builders."""

from __future__ import annotations

from itinerary_generation.summaries_core import (
    create_trip_glance,
    create_journey_arc,
    describe_city_experience,
    format_day_range,
    sanitize_journey_arc_experience,
)

__all__ = ['create_trip_glance', 'create_journey_arc', 'describe_city_experience', 'format_day_range', 'sanitize_journey_arc_experience']

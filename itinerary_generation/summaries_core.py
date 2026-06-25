"""Compatibility facade for :mod:`itinerary_generation.summaries`.

The implementation now lives in the responsibility-named module. This file
keeps legacy ``*_core`` imports working without becoming a catch-all again.
"""

from __future__ import annotations

from itinerary_generation.summaries import (
    create_trip_glance,
    _has,
    _add_theme,
    _welcome_arc_phrase,
    sanitize_journey_arc_experience,
    _title_case_arc,
    _compact_arc_phrase,
    describe_city_experience,
    format_day_range,
    create_journey_arc,
)

__all__ = ('create_trip_glance', '_has', '_add_theme', '_welcome_arc_phrase', 'sanitize_journey_arc_experience', '_title_case_arc', '_compact_arc_phrase', 'describe_city_experience', 'format_day_range', 'create_journey_arc',)

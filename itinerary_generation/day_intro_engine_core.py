"""Compatibility facade for :mod:`itinerary_generation.day_intro_engine`.

The implementation now lives in the responsibility-named module. This file
keeps legacy ``*_core`` imports working without becoming a catch-all again.
"""

from __future__ import annotations

from itinerary_generation.day_intro_engine import (
    _explicit_transfer_airport,
    _activity_day_intro,
    _group_tour_intro,
    _activity_intro,
    _group_tour_intro_from_source,
    _welcome_arrival_intro,
    _has_destination_hotel,
    _route_summary_from_rows,
    _premium_route_intro,
    _title_route_points,
    _travel_mode_from_title,
    _intro_for_title,
    create_day_intro,
)

__all__ = ('_explicit_transfer_airport', '_activity_day_intro', '_group_tour_intro', '_activity_intro', '_group_tour_intro_from_source', '_welcome_arrival_intro', '_has_destination_hotel', '_route_summary_from_rows', '_premium_route_intro', '_title_route_points', '_travel_mode_from_title', '_intro_for_title', 'create_day_intro',)

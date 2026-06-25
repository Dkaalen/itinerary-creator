"""Compatibility facade for client-facing day intro text."""

from __future__ import annotations

from itinerary_generation.day_intro_engine_core import (
    _activity_intro,
    _group_tour_intro_from_source,
    _intro_for_title,
    create_day_intro,
)

__all__ = ['_activity_intro', '_group_tour_intro_from_source', '_intro_for_title', 'create_day_intro']

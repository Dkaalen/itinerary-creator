"""Compatibility wrappers for day-planner intro helpers.

The actual intro wording rules live in ``day_intro_engine``. This module keeps
the existing private helper imports used by ``day_planner`` stable while avoiding
a second, drifting copy of the same rules.
"""

from __future__ import annotations

from itinerary_generation.day_intro_engine import (
    _activity_intro,
    _group_tour_intro_from_source,
    _intro_for_title,
)

__all__ = ["_activity_intro", "_group_tour_intro_from_source", "_intro_for_title"]

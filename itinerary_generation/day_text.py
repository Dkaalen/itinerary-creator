"""Compatibility facade for client-facing day intro text.

Day-intro generation lives in :mod:`itinerary_generation.day_intro_engine` so
planner hints, canonical day building, output edits and wrappers all share the
same wording rules. This module keeps the historical public import path stable.
"""

from __future__ import annotations

from itinerary_generation.day_activity_text import get_client_activity_phrase
from itinerary_generation.day_intro_engine import create_day_intro
from itinerary_generation.day_route_text import create_travel_route_label

__all__ = ["create_day_intro", "create_travel_route_label", "get_client_activity_phrase"]

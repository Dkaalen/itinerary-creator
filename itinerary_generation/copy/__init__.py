"""Deterministic client-facing copy composition helpers."""

from itinerary_generation.copy.activity_composition import client_activity_intro, client_group_tour_intro
from itinerary_generation.copy.visit_context import DayVisitContext, build_day_visit_contexts

__all__ = [
    "DayVisitContext",
    "build_day_visit_contexts",
    "client_activity_intro",
    "client_group_tour_intro",
]

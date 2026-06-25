"""Public compatibility facade for client-facing day intro text."""

from __future__ import annotations

from itinerary_generation.day_intro_activity import (
    _activity_day_intro,
    _activity_intro,
    _group_tour_intro,
    _group_tour_intro_from_source,
)
from itinerary_generation.day_intro_arrival import (
    _explicit_transfer_airport,
    _has_destination_hotel,
    _welcome_arrival_intro,
)
from itinerary_generation.day_intro_classification import _intro_for_title
from itinerary_generation.day_intro_orchestrator import create_day_intro
from itinerary_generation.day_intro_route import (
    _premium_route_intro,
    _route_summary_from_rows,
    _title_route_points,
    _travel_mode_from_title,
)

__all__ = [
    "_activity_day_intro",
    "_activity_intro",
    "_explicit_transfer_airport",
    "_group_tour_intro",
    "_group_tour_intro_from_source",
    "_has_destination_hotel",
    "_intro_for_title",
    "_premium_route_intro",
    "_route_summary_from_rows",
    "_title_route_points",
    "_travel_mode_from_title",
    "_welcome_arrival_intro",
    "create_day_intro",
]

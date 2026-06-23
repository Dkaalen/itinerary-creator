"""Destination-specific deterministic copy helpers.

Compatibility facade for the premium destination content layer.  Existing
renderers import this module; the real logic now lives in
``itinerary_generation.destination_content`` so copy is generated from the
shared Nordic destination registry instead of a small hardcoded city list.
"""

from __future__ import annotations

from typing import Iterable, Sequence

from itinerary_generation.destination_content import (
    destination_arc_fallback,
    destination_copy,
    leisure_description,
    travel_day_intro,
)
from itinerary_generation.destination_profiles import (
    destination_arrival_intro,
    destination_identity,
    destination_profile_for,
    destination_profiles,
    destination_stay_intro,
)

__all__ = [
    "destination_arc_fallback",
    "destination_arrival_intro",
    "destination_copy",
    "destination_identity",
    "destination_profile_for",
    "destination_profiles",
    "destination_stay_intro",
    "leisure_description",
    "travel_day_intro",
]

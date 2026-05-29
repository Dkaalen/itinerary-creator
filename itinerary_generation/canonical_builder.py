"""Compatibility facade for canonical itinerary builders."""

from __future__ import annotations

from itinerary_generation.canonical_accommodation import canonical_accommodation_block
from itinerary_generation.canonical_activity import canonical_activity_block
from itinerary_generation.canonical_day_builder import canonical_day
from itinerary_generation.canonical_helpers import _clean, _group_tour_pickup_window, _is_fløibanen, _row_id, _source_text
from itinerary_generation.canonical_inclusions import canonical_included_items, should_hide_note_row

__all__ = [
    "_clean",
    "_group_tour_pickup_window",
    "_is_fløibanen",
    "_row_id",
    "_source_text",
    "canonical_accommodation_block",
    "canonical_activity_block",
    "canonical_day",
    "canonical_included_items",
    "should_hide_note_row",
]

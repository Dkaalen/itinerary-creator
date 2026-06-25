"""Compatibility facade for client-facing activity titles."""

from __future__ import annotations

from itinerary_generation.activity_titles_core import (
    create_client_activity_title,
    is_bad_raw_day_title,
    normalize_client_day_title,
)

__all__ = ['create_client_activity_title', 'is_bad_raw_day_title', 'normalize_client_day_title']

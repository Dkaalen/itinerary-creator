"""Compatibility facade for structured itinerary documents."""

from __future__ import annotations

from shared.source_rows import source_row_id

from itinerary_generation.structured_builder_core import (
    build_itinerary_document,
)

__all__ = ['build_itinerary_document']

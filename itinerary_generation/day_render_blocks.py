"""Compatibility facade for UI-neutral itinerary day render blocks."""

from __future__ import annotations

from shared.source_rows import clean_text, source_row_id, source_text

from itinerary_generation.day_render_activity_blocks import (
    _is_blank_activity_row,
    _optional_title,
    build_cruise_leisure_render_block,
    build_included_today_render_block,
    build_leisure_render_block,
    build_optional_render_block,
)
from itinerary_generation.day_render_block_ordering import (
    _group_tour_start_time,
    _is_group_tour_overview_row,
    build_day_render_blocks,
)
from itinerary_generation.day_render_document_adapter import (
    _day_document_for,
    _output_edits_with_typed_day_overrides,
    _row_id,
    _rows_ordered_by_day_document,
    _travel_sequences_for_day,
    build_day_render_blocks_from_document,
    build_render_day,
    build_render_day_from_document,
)
from itinerary_generation.day_render_transport_blocks import build_arrival_render_block, build_departure_render_block

__all__ = [
    "_day_document_for",
    "_group_tour_start_time",
    "_is_blank_activity_row",
    "_is_group_tour_overview_row",
    "_optional_title",
    "_output_edits_with_typed_day_overrides",
    "_row_id",
    "_rows_ordered_by_day_document",
    "_travel_sequences_for_day",
    "clean_text",
    "source_row_id",
    "source_text",
    "build_arrival_render_block",
    "build_cruise_leisure_render_block",
    "build_day_render_blocks",
    "build_day_render_blocks_from_document",
    "build_departure_render_block",
    "build_included_today_render_block",
    "build_leisure_render_block",
    "build_optional_render_block",
    "build_render_day",
    "build_render_day_from_document",
]

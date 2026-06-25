"""Compatibility facade for :mod:`itinerary_generation.day_render_blocks`.

The implementation now lives in the responsibility-named module. This file
keeps legacy ``*_core`` imports working without becoming a catch-all again.
"""

from __future__ import annotations

from itinerary_generation.day_render_blocks import (
    _group_tour_start_time,
    _is_group_tour_overview_row,
    _is_blank_activity_row,
    build_leisure_render_block,
    build_cruise_leisure_render_block,
    build_arrival_render_block,
    build_departure_render_block,
    build_included_today_render_block,
    _optional_title,
    build_optional_render_block,
    build_day_render_blocks,
    _row_id,
    _day_document_for,
    _rows_ordered_by_day_document,
    _travel_sequences_for_day,
    _output_edits_with_typed_day_overrides,
    build_day_render_blocks_from_document,
    build_render_day_from_document,
    build_render_day,
)

__all__ = ('_group_tour_start_time', '_is_group_tour_overview_row', '_is_blank_activity_row', 'build_leisure_render_block', 'build_cruise_leisure_render_block', 'build_arrival_render_block', 'build_departure_render_block', 'build_included_today_render_block', '_optional_title', 'build_optional_render_block', 'build_day_render_blocks', '_row_id', '_day_document_for', '_rows_ordered_by_day_document', '_travel_sequences_for_day', '_output_edits_with_typed_day_overrides', 'build_day_render_blocks_from_document', 'build_render_day_from_document', 'build_render_day',)

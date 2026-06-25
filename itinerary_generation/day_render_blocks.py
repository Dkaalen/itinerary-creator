"""Compatibility facade for UI-neutral itinerary day render blocks."""

from __future__ import annotations

from itinerary_generation.day_render_blocks_core import (
    _is_blank_activity_row,
    _optional_title,
    build_leisure_render_block,
    build_cruise_leisure_render_block,
    build_arrival_render_block,
    build_departure_render_block,
    build_included_today_render_block,
    build_optional_render_block,
    build_day_render_blocks,
    build_day_render_blocks_from_document,
    build_render_day_from_document,
    build_render_day,
)

__all__ = ['_is_blank_activity_row', '_optional_title', 'build_leisure_render_block', 'build_cruise_leisure_render_block', 'build_arrival_render_block', 'build_departure_render_block', 'build_included_today_render_block', 'build_optional_render_block', 'build_day_render_blocks', 'build_day_render_blocks_from_document', 'build_render_day_from_document', 'build_render_day']

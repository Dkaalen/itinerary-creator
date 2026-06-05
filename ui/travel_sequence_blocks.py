"""Backward-compatible HTML facade for travel-arrangement sequence blocks."""

from __future__ import annotations

from itinerary_generation.travel_sequence_blocks import (
    _norway_nutshell_lines,
    build_travel_arrangements_render_block,
    get_travel_arrangement_line,
    get_travel_sequence_line,
    is_travel_sequence_candidate,
)
from ui.render_blocks import render_block_to_html


def build_travel_arrangements_block(travel_rows):
    block = build_travel_arrangements_render_block(travel_rows)
    return render_block_to_html(block) if block else None

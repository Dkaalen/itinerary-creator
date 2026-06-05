"""Backward-compatible HTML facade for day overview render blocks."""

from __future__ import annotations

from itinerary_generation.day_overview_blocks import (
    _client_title_case_fragment,
    _is_rental_overview,
    _join_rental_items,
    _polish_overview_item,
    _preserve_common_acronyms,
    _split_day_overview_items,
    build_day_overview_render_block,
)
from ui.render_blocks import render_block_to_html


def build_day_overview_block(row):
    block = build_day_overview_render_block(row)
    return render_block_to_html(block) if block else None

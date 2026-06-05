"""Backward-compatible HTML facade for standalone transport row blocks."""

from __future__ import annotations

from itinerary_generation.transport_render_blocks import (
    build_self_arranged_travel_render_block,
    build_self_transfer_render_block,
    build_transport_render_block,
    is_cruise_leisure_row as _is_cruise_leisure_row,
)
from ui.render_blocks import render_block_to_html


def build_transport_block(row, title_override=None):
    return render_block_to_html(build_transport_render_block(row, title_override=title_override))


def build_self_transfer_block(row, title_override=None):
    return render_block_to_html(build_self_transfer_render_block(row, title_override=title_override))


def build_self_arranged_travel_block(row, title_override=None):
    return render_block_to_html(build_self_arranged_travel_render_block(row, title_override=title_override))

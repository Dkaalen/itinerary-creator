"""Backward-compatible HTML facade for optional itinerary rows."""

from __future__ import annotations

from itinerary_generation.day_render_blocks import _optional_title, build_optional_render_block
from ui.render_blocks import render_block_to_html


def build_optional_day_block(row: dict) -> dict:
    return render_block_to_html(build_optional_render_block(row))

"""Backward-compatible HTML facade for simple day render blocks."""

from __future__ import annotations

from itinerary_generation.day_render_blocks import (
    build_arrival_render_block,
    build_cruise_leisure_render_block,
    build_departure_render_block,
    build_included_today_render_block,
    build_leisure_render_block,
)
from ui.render_blocks import render_block_to_html


def build_leisure_block(row=None):
    return render_block_to_html(build_leisure_render_block(row))


def build_cruise_leisure_block(row):
    return render_block_to_html(build_cruise_leisure_render_block(row))


def build_arrival_block(row):
    return render_block_to_html(build_arrival_render_block(row))


def build_departure_block(row):
    return render_block_to_html(build_departure_render_block(row))


def build_included_today_block(items):
    block = build_included_today_render_block(items)
    return render_block_to_html(block) if block else None

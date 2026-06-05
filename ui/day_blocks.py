"""Day block builders for itinerary HTML/UI output.

The day-page decisions now live in ``itinerary_generation.day_render_blocks`` as
UI-neutral RenderBlock objects.  This module is kept as the backward-compatible
HTML facade used by older tests and callers.
"""

from __future__ import annotations

from itinerary_generation.day_overview_blocks import build_day_overview_render_block
from itinerary_generation.day_render_blocks import (
    _is_blank_activity_row,
    build_day_render_blocks,
    build_included_today_render_block,
)
from ui.render_blocks import render_block_to_html


def build_activity_block(row):
    from ui.canonical_blocks import render_activity_block

    return render_activity_block(row)


def build_accommodation_block(row):
    from ui.canonical_blocks import render_accommodation_block

    return render_accommodation_block(row)


def build_day_overview_block(row):
    block = build_day_overview_render_block(row)
    return render_block_to_html(block) if block else None


def build_included_today_block(items):
    block = build_included_today_render_block(items)
    return render_block_to_html(block) if block else None


def build_leisure_block(row=None):
    from ui.simple_day_blocks import build_leisure_block as _build
    return _build(row)


def build_cruise_leisure_block(row):
    from ui.simple_day_blocks import build_cruise_leisure_block as _build
    return _build(row)


def build_arrival_block(row):
    from ui.simple_day_blocks import build_arrival_block as _build
    return _build(row)


def build_departure_block(row):
    from ui.simple_day_blocks import build_departure_block as _build
    return _build(row)


def build_optional_day_block(row):
    from ui.optional_day_blocks import build_optional_day_block as _build
    return _build(row)


def build_travel_arrangements_block(travel_rows):
    from ui.travel_sequence_blocks import build_travel_arrangements_block as _build
    return _build(travel_rows)


def build_day_blocks(rows):
    return [render_block_to_html(block) for block in build_day_render_blocks(rows) if block]

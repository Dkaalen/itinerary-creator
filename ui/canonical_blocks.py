"""Compatibility shims for canonical itinerary block renderers.

The concrete renderers now live in narrower modules. Keep these names here so
existing callers can continue importing from ``ui.canonical_blocks`` while the
larger day-block orchestration is split in small steps.
"""


def render_activity_block(row):
    """Render an activity block via the extracted activity renderer."""

    from ui.activity_blocks import render_activity_block as _render_activity_block

    return _render_activity_block(row)


def render_accommodation_block(row):
    """Render an accommodation block via the extracted accommodation renderer."""

    from ui.accommodation_blocks import render_accommodation_block as _render_accommodation_block

    return _render_accommodation_block(row)


__all__ = ["render_activity_block", "render_accommodation_block"]

"""Compatibility imports for canonical itinerary block renderers.

The concrete renderers now live in narrower modules. Keep these names here so
existing callers can continue importing from ``ui.canonical_blocks`` while the
larger day-block orchestration is split in small steps.
"""

from ui.accommodation_blocks import render_accommodation_block
from ui.activity_blocks import render_activity_block

__all__ = ["render_activity_block", "render_accommodation_block"]

"""Compatibility facade for canonical transport sequence builders."""

from __future__ import annotations

from itinerary_generation.transport_domain.render import (
    _norway_nutshell_lines,
    build_travel_arrangements_render_block,
    get_travel_arrangement_line,
    get_travel_sequence_line,
    is_travel_sequence_candidate,
)

__all__ = [
    "_norway_nutshell_lines",
    "build_travel_arrangements_render_block",
    "get_travel_arrangement_line",
    "get_travel_sequence_line",
    "is_travel_sequence_candidate",
]

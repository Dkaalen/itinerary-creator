"""Backward-compatible facade for transport and travel-arrangement blocks."""

from __future__ import annotations

from ui.transport_row_blocks import (
    _is_cruise_leisure_row,
    build_self_arranged_travel_block,
    build_self_transfer_block,
    build_transport_block,
)
from ui.travel_sequence_blocks import (
    build_travel_arrangements_block,
    get_travel_arrangement_line,
    get_travel_sequence_line,
    is_travel_sequence_candidate,
)

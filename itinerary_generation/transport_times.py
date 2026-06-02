"""Shared transport schedule display helpers."""

from __future__ import annotations

from parser_modules.time_finders import find_clock_range
from parser_modules.time_normalize import normalize_time_text
from itinerary_generation.transport_routes import _transport_source_text
from .inclusion_utils import clean


def get_transport_time_text(row: dict) -> str:
    """Return a client-facing time range for transport rows.

    Some supplier transport rows include schedule text only in the raw details.
    Keep one shared fallback so day pages and final inclusions do not drift.
    """

    time = clean(row.get("time", ""))
    if time:
        return time
    source = _transport_source_text(row)
    clock_range = find_clock_range(source)
    if clock_range:
        return normalize_time_text(clock_range)
    return ""

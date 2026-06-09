"""Time normalization helpers."""

from __future__ import annotations

from text_polish import expand_time_with_duration, format_duration_display
from normalizer_modules.text_utils import get_row_type


def expand_single_start_time_with_duration(time_value: str, duration_value: str) -> str:
    """Return a start-end time range when time + duration are reliable."""
    return expand_time_with_duration(time_value, duration_value)


def normalize_activity_display_time_fields(row: dict) -> dict:
    """Populate activity display timing fields from normalized source fields.

    ``time`` and ``duration`` remain the editable/source values. ``display_time``
    and ``display_duration`` are the renderer contract. This keeps time-range
    expansion upstream of rendering/editor repair logic while preserving the
    original start time for editing.
    """
    if get_row_type(row) != "Activity":
        return row

    time_value = row.get("time", "")
    duration_value = row.get("duration", "")
    row["display_time"] = expand_single_start_time_with_duration(time_value, duration_value) if time_value else ""
    row["display_duration"] = format_duration_display(duration_value) if duration_value else ""
    return row


def normalize_time_range_fields(row: dict) -> dict:
    """Compatibility wrapper for the activity display-time normalizer."""
    return normalize_activity_display_time_fields(row)

"""Time normalization helpers."""

from text_polish import expand_time_with_duration
from normalizer_modules.text_utils import get_row_type

def expand_single_start_time_with_duration(time_value: str, duration_value: str) -> str:
    """Return a start-end time range when time + duration are reliable."""
    return expand_time_with_duration(time_value, duration_value)

def normalize_time_range_fields(row: dict) -> dict:
    """Normalize activity time display before rendering/exporting."""
    if get_row_type(row) != "Activity":
        return row
    row["time"] = expand_single_start_time_with_duration(row.get("time", ""), row.get("duration", ""))
    return row


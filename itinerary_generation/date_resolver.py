"""Resolve client-facing itinerary dates from parsed rows."""
from __future__ import annotations

from itinerary_generation.date_formatting import format_client_date, format_client_date_range, parse_date
from itinerary_generation.common import get_row_type


def _row_start(row: dict):
    return parse_date(row.get("start_date"))


def _row_end(row: dict):
    return parse_date(row.get("end_date")) or parse_date(row.get("start_date"))


def get_day_date_text(rows: list[dict]) -> str:
    """Return the display date for one itinerary day, if available."""

    for row in rows or []:
        if get_row_type(row) == "Hotel":
            text = format_client_date(row.get("start_date"))
        else:
            text = format_client_date_range(row.get("start_date"), row.get("end_date"))
        if text:
            return text
    for row in rows or []:
        text = format_client_date(row.get("end_date"))
        if text:
            return text
    return ""


def get_trip_date_range_text(rows: list[dict]) -> str:
    """Return the display date range for the full trip, if available."""

    starts = [_row_start(row) for row in rows or []]
    ends = [_row_end(row) for row in rows or []]
    starts = [value for value in starts if value]
    ends = [value for value in ends if value]
    if not starts and not ends:
        return ""
    start = min(starts or ends)
    end = max(ends or starts)
    return format_client_date_range(start, end)

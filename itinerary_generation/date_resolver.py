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

    dated_days = []
    for row in rows or []:
        day_text = str(row.get("day", "") or "")
        import re
        match = re.search(r"\d+", day_text)
        value = _row_start(row)
        if match and value:
            dated_days.append((int(match.group()), value))
    if dated_days:
        by_day = {}
        for day_number, value in dated_days:
            by_day.setdefault(day_number, value)
        ordered = [by_day[key] for key in sorted(by_day)]
        # Use itinerary order rather than a stray maximum year. Chronology
        # validation reports contradictory source dates separately.
        start, end = ordered[0], ordered[-1]
    else:
        starts = [value for value in (_row_start(row) for row in rows or []) if value]
        ends = [value for value in (_row_end(row) for row in rows or []) if value]
        if not starts and not ends:
            return ""
        start, end = min(starts or ends), max(ends or starts)
    if start.year != end.year:
        return f"{format_client_date(start)} {start.year} - {format_client_date(end)} {end.year}"
    return format_client_date_range(start, end)

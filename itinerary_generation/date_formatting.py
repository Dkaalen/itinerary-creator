"""Client-facing date formatting helpers."""
from __future__ import annotations

from datetime import date, datetime


def ordinal_day(day: int) -> str:
    """Return an ordinal day number such as 1st, 2nd, 3rd or 4th."""

    if 10 <= day % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{day}{suffix}"


def parse_date(value: object) -> date | None:
    """Parse common itinerary date values without raising on blanks."""

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y", "%d-%m-%Y", "%B %d, %Y", "%d %B %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def format_client_date(value: object) -> str:
    """Format a date as `1st of January` for client-facing output."""

    parsed = parse_date(value)
    if not parsed:
        return ""
    return f"{ordinal_day(parsed.day)} of {parsed.strftime('%B')}"


def format_client_date_range(start: object, end: object) -> str:
    """Format a client-facing date range such as `1st of January - 6th of January`."""

    start_text = format_client_date(start)
    end_text = format_client_date(end)
    if start_text and end_text and start_text != end_text:
        return f"{start_text} - {end_text}"
    return start_text or end_text

"""Time and duration display helpers for UI rendering."""

from __future__ import annotations

import re

from itinerary_parser import normalize_time_text
from text_polish import expand_time_with_duration
from itinerary_generation.common import get_row_type
from ui.transport_display_helpers import is_tallinn_ferry_day_trip


def display_time(value):
    return normalize_time_text(value)


def display_time_with_duration(time_value, duration_value):
    """Show a clear start-end time when a reliable start time and duration exist.

    This is the single day-by-day display rule the user requested:
    if an activity has one start time plus a duration, show the calculated
    end time in the Time line.
    """
    return expand_time_with_duration(display_time(time_value), duration_value)


def get_time_period(time_text):
    if not time_text:
        return "Featured experience"

    text = time_text.lower()
    match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", text)

    if not match:
        # 24-hour format support.
        match_24 = re.search(r"\b(\d{1,2}):(\d{2})\b", text)
        if not match_24:
            return "Featured experience"

        hour = int(match_24.group(1))
    else:
        hour = int(match.group(1))
        period = match.group(3)

        if period == "pm" and hour != 12:
            hour += 12

        if period == "am" and hour == 12:
            hour = 0

    if hour < 12:
        return "Morning Experience"

    if 12 <= hour < 17:
        return "Afternoon Experience"

    return "Evening Experience"


def get_activity_duration_label(row, duration):
    """Return a conservative client-facing duration label for an activity.

    Most experiences should simply say "Duration". A tour can include a ferry,
    canal boat, or cruise element without the full activity length being a
    ferry/cruise duration. Use ferry/cruise labels only when the row or duration
    text clearly supports that wording.
    """

    row_type = get_row_type(row)
    duration_text = str(duration or "").lower().strip()

    if is_tallinn_ferry_day_trip(row):
        return "Ferry duration"

    if re.match(r"^ferry\s+duration\b", duration_text, flags=re.IGNORECASE):
        return "Ferry duration"

    if re.match(r"^cruise\s+duration\b", duration_text, flags=re.IGNORECASE):
        return "Cruise duration"

    if row_type == "Ferry":
        return "Ferry duration"

    if row_type == "Cruise":
        return "Cruise duration"

    return "Duration"

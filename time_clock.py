"""Shared clock/time-range helpers."""

from __future__ import annotations

import re

from time_duration import parse_duration_minutes
from time_text import clean_time_text


def has_time_range(value: str) -> bool:
    text = clean_time_text(value)
    return bool(re.search(r"\d\s*(?:-|–)\s*\d", text))


def has_time_alternatives(value: str) -> bool:
    return "/" in clean_time_text(value)


def _normalize_clock_token(value: str) -> str:
    text = clean_time_text(value)
    match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*([AaPp])\.?[Mm]?\.?", text)
    if not match:
        match = re.fullmatch(r"(\d{1,2}):(\d{2})", text)
        if not match:
            return ""
        hour = int(match.group(1))
        minute = int(match.group(2))
        suffix = "AM" if hour < 12 else "PM"
        hour12 = hour % 12 or 12
        return f"{hour12}:{minute:02d} {suffix}"

    hour = int(match.group(1))
    minute = int(match.group(2) or "0")
    suffix = match.group(3).upper() + "M"
    if hour < 1 or hour > 12 or minute > 59:
        return ""
    return f"{hour}:{minute:02d} {suffix}"


def _clock_to_minutes(value: str):
    text = clean_time_text(value)
    match = re.fullmatch(r"(\d{1,2}):(\d{2})\s*(AM|PM)", text, flags=re.IGNORECASE)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2))
    suffix = match.group(3).upper()
    if suffix == "PM" and hour != 12:
        hour += 12
    if suffix == "AM" and hour == 12:
        hour = 0
    return hour * 60 + minute


def _minutes_to_clock(total_minutes: int) -> str:
    total_minutes = total_minutes % (24 * 60)
    hour24 = total_minutes // 60
    minute = total_minutes % 60
    suffix = "AM" if hour24 < 12 else "PM"
    hour12 = hour24 % 12 or 12
    return f"{hour12}:{minute:02d} {suffix}"


def expand_time_with_duration(time_value: str, duration_value: str) -> str:
    """Display start-end time when a single start time and duration are known."""

    raw_time = clean_time_text(time_value)
    if not raw_time:
        return ""

    if has_time_range(raw_time) or has_time_alternatives(raw_time):
        return raw_time

    start_display = _normalize_clock_token(raw_time)
    if not start_display:
        return raw_time

    start_minutes = _clock_to_minutes(start_display)
    duration_minutes = parse_duration_minutes(duration_value)
    if start_minutes is None or duration_minutes is None:
        return start_display

    if duration_minutes < 15 or duration_minutes > 18 * 60:
        return start_display

    return f"{start_display} - {_minutes_to_clock(start_minutes + duration_minutes)}"

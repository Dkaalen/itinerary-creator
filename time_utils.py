"""
time_utils.py

Shared time and duration helpers for itinerary output.

This module is intentionally small and deterministic. Parser, normalizer,
HTML preview and PDF export should all use these helpers so duration handling
cannot regress in one layer while working in another.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


_DURATION_LABEL_RE = re.compile(
    r"^(?:duration|tour duration|ferry duration|cruise duration)\s*:?\s*",
    flags=re.IGNORECASE,
)


def clean_time_text(value: str) -> str:
    text = " ".join(str(value or "").replace("\xa0", " ").split()).strip()
    # Some general text polish can turn decimal durations into "5. 5 Hrs".
    # Normalize that back before duration parsing so all layers see 5.5 hours.
    text = re.sub(r"(\d)\s*([\.,])\s*(\d)", r"\1.\3", text)
    return text


def _normalize_decimal(value: str) -> Decimal | None:
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


def _parse_hour_duration_minutes(value: str) -> int | None:
    """Parse supplier hour values into minutes.

    Decimal-looking durations such as 2.15 Hr are often colleague shorthand for
    2 hours 15 minutes, not 2.15 decimal hours. We treat two-digit fractional
    parts below 60 as clock-style minutes, while preserving normal decimal
    values such as 2.5 Hr -> 2 hours 30 minutes.
    """

    text = str(value or "").replace(",", ".").strip()
    match = re.fullmatch(r"(\d+)(?:\.(\d+))?", text)
    if not match:
        return None

    hours = int(match.group(1))
    fraction = match.group(2) or ""
    if not fraction:
        return hours * 60

    if len(fraction) == 2:
        minute_value = int(fraction)
        if 0 <= minute_value < 60:
            return hours * 60 + minute_value

    decimal_hours = _normalize_decimal(text)
    if decimal_hours is None:
        return None
    return int((decimal_hours * Decimal(60)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def parse_duration_minutes(value: str):
    """Return duration in minutes for common supplier duration strings.

    Supports whole and decimal hours, comma decimals and explicit minutes:
    5 Hrs, 5.5 Hrs, 1,5 hours, 4 hours 30 minutes, 5-8 minutes.
    """

    text = clean_time_text(value).lower()
    if not text:
        return None

    text = _DURATION_LABEL_RE.sub("", text)
    text = text.replace("½", ".5")

    range_minutes = re.search(
        r"\b(\d+)\s*(?:-|–)\s*(\d+)\s*(?:minutes?|mins?|min|m)\b",
        text,
        flags=re.IGNORECASE,
    )
    if range_minutes:
        # Ranges such as 5-8 minutes are approximate. Use the upper bound for
        # duration math only if this is ever used as a timed experience.
        return int(range_minutes.group(2))

    total = 0

    hour_match = re.search(
        r"\b(\d+(?:[\.,]\d+)?)\s*(?:hours?|hrs?|hr|h)\b",
        text,
        flags=re.IGNORECASE,
    )
    if hour_match:
        hour_minutes = _parse_hour_duration_minutes(hour_match.group(1))
        if hour_minutes is not None:
            total += hour_minutes

    minute_match = re.search(
        r"\b(\d+)\s*(?:minutes?|mins?|min|m)\b",
        text,
        flags=re.IGNORECASE,
    )
    if minute_match:
        total += int(minute_match.group(1))

    return total or None


def format_duration_minutes(total_minutes: int) -> str:
    """Format duration minutes as clean client-facing text."""

    try:
        minutes = int(total_minutes)
    except (TypeError, ValueError):
        return ""

    if minutes <= 0:
        return ""

    hours, remainder = divmod(minutes, 60)
    parts = []
    if hours:
        parts.append(f"{hours} {'hour' if hours == 1 else 'hours'}")
    if remainder:
        parts.append(f"{remainder} {'minute' if remainder == 1 else 'minutes'}")
    return " ".join(parts)


def format_duration_display(value: str) -> str:
    """Normalize supplier duration text into clean client-facing duration text.

    Examples:
    5.5 Hrs -> 5 hours 30 minutes
    1.5 hours -> 1 hour 30 minutes
    Duration: 4 hours -> 4 hours
    5-8 minutes -> 5–8 minutes
    """

    raw = clean_time_text(value)
    if not raw:
        return ""

    label_stripped = _DURATION_LABEL_RE.sub("", raw).strip(" -|:")

    # Preserve explicit duration ranges as ranges. Do this before converting to
    # minutes, otherwise a supplier value such as "2.5 -3.5h" collapses to the
    # upper bound ("3 hours 30 minutes") and loses important client-facing
    # uncertainty. This is a general duration rule, not tied to any itinerary.
    hour_range = re.search(
        r"\b(\d+(?:\s*[.,]\s*\d+)?)\s*(?:-|–|to)\s*(\d+(?:\s*[.,]\s*\d+)?)\s*(?:h|hr|hrs|hour|hours)\b",
        label_stripped,
        flags=re.IGNORECASE,
    )
    if hour_range:
        start = re.sub(r"\s*([.,])\s*", r"\1", hour_range.group(1)).replace(",", ".")
        end = re.sub(r"\s*([.,])\s*", r"\1", hour_range.group(2)).replace(",", ".")
        return f"{start}–{end} hours"

    minute_range = re.search(
        r"\b(\d+)\s*(?:-|–)\s*(\d+)\s*(minutes?)\b",
        label_stripped,
        flags=re.IGNORECASE,
    )
    if minute_range:
        return f"{minute_range.group(1)}–{minute_range.group(2)} minutes"

    minutes = parse_duration_minutes(raw)
    if minutes is not None:
        return format_duration_minutes(minutes)

    cleaned = re.sub(r"\bHrs?\b", "hours", label_stripped, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bHr\b", "hour", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -|:")
    return cleaned


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

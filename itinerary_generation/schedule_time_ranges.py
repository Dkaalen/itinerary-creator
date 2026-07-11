"""Parse supplier activity time ranges into neutral schedule facts.

This module owns AM/PM range interpretation.  It deliberately distinguishes a
real overnight range from a reversed daytime range so Schedule Brain does not
turn bad supplier data into a fictitious next-day activity.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_TIME_RE = re.compile(r"\b(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<suffix>am|pm)\b", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedTimeRange:
    start_minutes: int | None = None
    end_minutes: int | None = None
    is_overnight: bool = False
    is_invalid: bool = False
    reason: str = ""


def _minutes(match: re.Match[str]) -> int:
    hour = int(match.group("hour"))
    minute = int(match.group("minute") or "0")
    if hour > 12 or minute > 59:
        raise ValueError("invalid clock value")
    suffix = match.group("suffix").casefold()
    if suffix == "pm" and hour != 12:
        hour += 12
    elif suffix == "am" and hour == 12:
        hour = 0
    return hour * 60 + minute


def parse_time_range(value: object) -> ParsedTimeRange:
    text = str(value or "")
    matches = list(_TIME_RE.finditer(text))
    if not matches:
        return ParsedTimeRange()
    try:
        start = _minutes(matches[0])
        end = _minutes(matches[1]) if len(matches) > 1 else None
    except ValueError:
        return ParsedTimeRange(is_invalid=True, reason="invalid_clock_value")
    if end is None:
        return ParsedTimeRange(start_minutes=start)
    if end >= start:
        duration = end - start
        if duration > 16 * 60:
            return ParsedTimeRange(start, end, is_invalid=True, reason="implausibly_long_range")
        return ParsedTimeRange(start, end)

    # Only an evening-to-early-morning range is safely interpreted as
    # crossing midnight.  A morning-to-earlier-afternoon reversal is bad data.
    if start >= 17 * 60 and end <= 6 * 60:
        return ParsedTimeRange(start, end + 24 * 60, is_overnight=True)
    return ParsedTimeRange(start, end, is_invalid=True, reason="reversed_daytime_range")


__all__ = ["ParsedTimeRange", "parse_time_range"]

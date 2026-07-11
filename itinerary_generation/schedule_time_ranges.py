"""Parse supplier time ranges into neutral schedule facts.

The contract accepts common supplier formats (AM/PM, 24-hour, and dotted
24-hour clocks) and distinguishes absent, malformed, overnight, and reversed
ranges.  Schedule and QA consumers share this parser instead of implementing
independent time heuristics.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_CLOCK = r"(?P<{prefix}hour>\d{{1,2}})(?:(?P<{prefix}sep>[:.])(?P<{prefix}minute>\d{{2}}))?\s*(?P<{prefix}suffix>a\.?m\.?|p\.?m\.?)?"
_RANGE_RE = re.compile(
    rf"(?<![\d.]){_CLOCK.format(prefix='start_')}\s*(?:-|–|—|\bto\b)\s*{_CLOCK.format(prefix='end_')}(?![\d.])",
    re.IGNORECASE,
)
_SINGLE_RE = re.compile(rf"(?<![\d.]){_CLOCK.format(prefix='single_')}(?![\d.])", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedTimeRange:
    start_minutes: int | None = None
    end_minutes: int | None = None
    is_overnight: bool = False
    is_invalid: bool = False
    reason: str = ""
    source_format: str = ""


def _normalise_suffix(value: str | None) -> str:
    return re.sub(r"[^apm]", "", str(value or "").casefold())


def _minutes(match: re.Match[str], prefix: str) -> int:
    hour = int(match.group(f"{prefix}hour"))
    minute = int(match.group(f"{prefix}minute") or "0")
    suffix = _normalise_suffix(match.group(f"{prefix}suffix"))
    if minute > 59:
        raise ValueError("invalid clock value")
    if suffix:
        if hour < 1 or hour > 12:
            raise ValueError("invalid clock value")
        if suffix == "pm" and hour != 12:
            hour += 12
        elif suffix == "am" and hour == 12:
            hour = 0
    elif hour > 23:
        raise ValueError("invalid clock value")
    return hour * 60 + minute


def _format_for(match: re.Match[str]) -> str:
    if match.group("start_suffix") or match.group("end_suffix"):
        return "ampm"
    if match.group("start_sep") == "." or match.group("end_sep") == ".":
        return "24h_dotted"
    return "24h"


def _validated_range(start: int, end: int, *, source_format: str) -> ParsedTimeRange:
    if end >= start:
        duration = end - start
        if duration > 20 * 60:
            return ParsedTimeRange(start, end, is_invalid=True, reason="implausibly_long_range", source_format=source_format)
        return ParsedTimeRange(start, end, source_format=source_format)

    # Only an evening-to-early-morning range is safely interpreted as crossing
    # midnight.  A daytime reversal remains invalid supplier data.
    if start >= 17 * 60 and end <= 6 * 60:
        return ParsedTimeRange(start, end + 24 * 60, is_overnight=True, source_format=source_format)
    return ParsedTimeRange(start, end, is_invalid=True, reason="reversed_daytime_range", source_format=source_format)


def parse_time_range(value: object) -> ParsedTimeRange:
    text = str(value or "")
    match = _RANGE_RE.search(text)
    if match:
        try:
            start = _minutes(match, "start_")
            end = _minutes(match, "end_")
        except ValueError:
            return ParsedTimeRange(is_invalid=True, reason="invalid_clock_value")
        return _validated_range(start, end, source_format=_format_for(match))

    # A single explicit clock is still useful for ordering.  Require either a
    # suffix or a clock separator so ordinary numbers/day labels are ignored.
    single = _SINGLE_RE.search(text)
    if not single or not (single.group("single_suffix") or single.group("single_sep")):
        return ParsedTimeRange()
    try:
        start = _minutes(single, "single_")
    except ValueError:
        return ParsedTimeRange(is_invalid=True, reason="invalid_clock_value")
    suffix = single.group("single_suffix")
    source_format = "ampm" if suffix else "24h_dotted" if single.group("single_sep") == "." else "24h"
    return ParsedTimeRange(start_minutes=start, source_format=source_format)


__all__ = ["ParsedTimeRange", "parse_time_range"]

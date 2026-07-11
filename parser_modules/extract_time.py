"""Time and duration extraction helpers for supplier activity text.

This module is intentionally focused on temporal fields only.  The public
compatibility facade remains :mod:`parser_modules.extractors`.
"""

from __future__ import annotations

import re

from parser_modules.common import clean_space
from parser_modules.details import extract_detail
from parser_modules.time_parsing import (
    find_clock_range,
    find_parallel_clock_ranges,
    find_single_clock_time,
    normalize_duration_text,
    normalize_time_text,
    split_time_and_duration,
)


def looks_like_pickup_window(text: str) -> bool:
    """Return True for timing snippets that describe logistics, not duration."""

    lower = str(text or "").lower()
    return "before departure" in lower or "pick-up window" in lower or "pickup window" in lower


def extract_duration_from_description(main_text: str) -> str:
    """Extract a client-facing activity duration from supplier text."""

    main_text = re.sub(r"(\d)\s*\.\s*(\d)", r"\1.\2", str(main_text or ""))
    standard_time = extract_detail(main_text, "Time")
    _, duration = split_time_and_duration(standard_time)
    if duration:
        return duration

    # Prefer explicit duration labels, especially when supplier text also
    # contains pick-up windows such as "75–45 minutes before departure".
    explicit_patterns = [
        r"\bDuration\s*:?\s*(\d+(?:\s*[.,]\s*\d+)?\s*(?:-|–|to)\s*\d+(?:\s*[.,]\s*\d+)?\s*(?:Hrs|Hr|hours|hour|h))\b",
        r"\bDuration\s*:?\s*(\d+(?:\s*[.,]\s*\d+)?\s*(?:Hrs|Hr|hours|hour|h))\b",
    ]
    for pattern in explicit_patterns:
        match = re.search(pattern, main_text, flags=re.IGNORECASE)
        if match:
            return normalize_duration_text(match.group(1))

    pipe_parts = [clean_space(part) for part in main_text.split("|")]
    for part in pipe_parts[1:5]:
        if looks_like_pickup_window(part):
            continue
        match = re.search(
            r"\b((?:Cruise\s+Duration|Tour\s+Duration|Duration)?\s*:?\s*\d+(?:\s*[.,]\s*\d+)?\s*(?:-|–|to)?\s*\d*(?:\s*[.,]\s*\d+)?\s*(?:Hrs|Hr|hours|hour|h))\b",
            part,
            flags=re.IGNORECASE,
        )
        if match:
            return normalize_duration_text(match.group(1))

    match = re.search(
        r"\b((?:Cruise\s+Duration|Tour\s+Duration|Duration)?\s*:?\s*\d+(?:\s*[.,]\s*\d+)?\s*(?:-|–|to)?\s*\d*(?:\s*[.,]\s*\d+)?\s*(?:Hrs|Hr|hours|hour|h))\b",
        main_text,
        flags=re.IGNORECASE,
    )
    if match and not looks_like_pickup_window(main_text[match.start() : match.end() + 40]):
        return normalize_duration_text(match.group(1))

    minute_match = re.search(r"\b(\d+\s*(?:-|–)\s*\d+\s*minutes?)\b", main_text, flags=re.IGNORECASE)
    if minute_match and not looks_like_pickup_window(main_text[minute_match.start() : minute_match.end() + 40]):
        return normalize_duration_text(minute_match.group(1))

    return ""


def extract_time_from_description(main_text: str) -> str:
    """Extract the primary start time or time range from supplier text."""

    standard_time = extract_detail(main_text, "Time")

    if standard_time:
        parallel_ranges = find_parallel_clock_ranges(standard_time)
        if parallel_ranges:
            return " / ".join(normalize_time_text(clock_range) for clock_range in parallel_ranges)
        clock_range = find_clock_range(standard_time)
        if clock_range:
            return normalize_time_text(clock_range)
        single_time = find_single_clock_time(standard_time)
        if single_time:
            return normalize_time_text(single_time)
        time_text, _ = split_time_and_duration(standard_time)
        return time_text

    # Pipe format examples:
    # "Title | 20:00 | 5 Hrs | ..."
    # "Title | 8-10 AM (Anytime) | 7 Hrs | ..."
    # "Oslo to Bergen | Norway in a Nutshell 08:25 - 20:40 | ..."
    pipe_parts = [clean_space(part) for part in main_text.split("|")]

    for part in pipe_parts[1:4]:
        lower = part.lower()
        if "hr" in lower or "hour" in lower or "minute" in lower:
            continue
        clock_range = find_clock_range(part)
        if clock_range:
            return normalize_time_text(clock_range)
        if re.search(r"\b12\s+noon\b|\bnoon\b", part, flags=re.IGNORECASE):
            return "12:00 PM"
        single_time = find_single_clock_time(part)
        if single_time:
            return normalize_time_text(single_time)
        spaced_time = re.match(r"^\s*(\d{1,2})\s+(\d{2})\s*(?:([AaPp]\.?[Mm]\.?))?\s*$", part)
        if spaced_time:
            suffix = spaced_time.group(3) or ""
            return normalize_time_text(f"{spaced_time.group(1)}:{spaced_time.group(2)} {suffix}".strip())

    clock_range = find_clock_range(main_text)
    if clock_range:
        return normalize_time_text(clock_range.replace(".", ":"))

    return ""


__all__ = [
    "extract_duration_from_description",
    "extract_time_from_description",
    "looks_like_pickup_window",
]

"""Clock token parsing and formatting helpers."""

from __future__ import annotations

import re

from parser_modules.common import clean_space


def normalize_ampm(value):
    suffix = str(value or "").replace(".", "").upper()
    if suffix in {"AM", "PM"}:
        return suffix
    return ""


def parse_time_token(value):
    text = clean_space(value)
    match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*([AaPp]\.?[Mm]\.?)?", text)
    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2) or "0")
    suffix = normalize_ampm(match.group(3) or "")

    if hour > 24 or minute > 59:
        return None

    return {
        "hour": hour,
        "minute": minute,
        "suffix": suffix,
        "raw": text,
    }


def format_12_hour(hour, minute, suffix=""):
    suffix = normalize_ampm(suffix)

    if suffix:
        display_hour = hour
        if display_hour == 0:
            display_hour = 12
        if display_hour > 12:
            display_hour = display_hour - 12
        return f"{display_hour}:{minute:02d} {suffix}"

    # Treat suffix-free times as 24-hour values. This standardizes colleague
    # inputs like 20:00, 18:00, and 08:30 - 22:30 into client-facing AM/PM.
    if hour == 0:
        return f"12:{minute:02d} AM"
    if 1 <= hour < 12:
        return f"{hour}:{minute:02d} AM"
    if hour == 12:
        return f"12:{minute:02d} PM"
    return f"{hour - 12}:{minute:02d} PM"


def format_time_token(value, default_suffix=""):
    parsed = parse_time_token(value)
    if not parsed:
        return clean_space(value)

    suffix = parsed["suffix"] or normalize_ampm(default_suffix)
    return format_12_hour(parsed["hour"], parsed["minute"], suffix)


def infer_range_suffixes(start, end):
    start_suffix = start["suffix"]
    end_suffix = end["suffix"]

    if start_suffix and not end_suffix:
        if start_suffix == "AM" and end["hour"] <= start["hour"]:
            end_suffix = "PM"
        else:
            end_suffix = start_suffix

    if end_suffix and not start_suffix:
        if end_suffix == "PM" and start["hour"] > end["hour"]:
            start_suffix = "AM"
        else:
            start_suffix = end_suffix

    return start_suffix, end_suffix



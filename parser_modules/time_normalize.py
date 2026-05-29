"""Client-facing time normalization helpers."""

from __future__ import annotations

import re

from parser_modules.common import clean_space
from parser_modules.time_tokens import format_time_token, infer_range_suffixes, parse_time_token


def normalize_time_text(value):
    """Standardize itinerary times to AM/PM display format.

    Examples:
    20:00 -> 8:00 PM
    08:30 - 22:30 -> 8:30 AM - 10:30 PM
    7 PM -> 7:00 PM
    8-10 AM -> 8:00 AM - 10:00 AM
    """

    text = clean_space(value)
    if not text:
        return ""

    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+", " ", text).strip()

    time_token = r"\d{1,2}(?::\d{2})?\s*(?:[AaPp]\.?[Mm]\.?)?"
    range_pattern = re.compile(
        rf"(?<!\d)({time_token})\s*-\s*({time_token})(?!\d)",
        flags=re.IGNORECASE,
    )

    def replace_range(match):
        raw_range = match.group(0)
        after = text[match.end():match.end() + 15].lower()
        if "minute" in after or "min" in after:
            return raw_range
        if ":" not in raw_range and not re.search(r"[AaPp]\.?[Mm]\.?", raw_range):
            return raw_range

        start_raw = match.group(1)
        end_raw = match.group(2)
        start = parse_time_token(start_raw)
        end = parse_time_token(end_raw)

        if not start or not end:
            return raw_range

        start_suffix, end_suffix = infer_range_suffixes(start, end)
        return f"{format_time_token(start_raw, start_suffix)} - {format_time_token(end_raw, end_suffix)}"

    text = range_pattern.sub(replace_range, text)

    # Normalize slash-separated alternatives and single remaining time tokens.
    single_pattern = re.compile(
        r"(?<!\d)(\d{1,2}(?::\d{2})?\s*(?:[AaPp]\.?[Mm]\.?|))(?!\s*(?:hours?|hrs?|hr)\b)(?!\d)",
        flags=re.IGNORECASE,
    )

    def replace_single(match):
        token = match.group(1).strip()
        parsed = parse_time_token(token)
        if not parsed:
            return match.group(0)

        # Avoid turning plain duration-like numbers into times. Single tokens
        # without AM/PM or a colon are too ambiguous to standardize safely.
        if not parsed["suffix"] and ":" not in token:
            return match.group(0)

        return format_time_token(token)

    text = single_pattern.sub(replace_single, text)
    text = re.sub(r"\(\s*anytime\s*\)", ", flexible start", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*,\s*flexible start", ", flexible start", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*/\s*", " / ", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+\)", ")", text)
    return text.strip(" ,")



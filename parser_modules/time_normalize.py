"""Client-facing time normalization helpers."""

from __future__ import annotations

import re

from parser_modules.common import clean_space
from parser_modules.time_tokens import format_time_token, infer_range_suffixes, parse_time_token


def _strip_supplier_warning_time_text(text: str) -> str:
    """Return a reliable clock value or blank from supplier warning text."""

    lower = text.lower()
    warning_markers = (
        "before departure",
        "bring warm clothes",
        "please arrive",
        "meeting point",
        "subject to",
        "voucher",
        "pickup window",
        "pick-up window",
    )
    if not any(marker in lower for marker in warning_markers) and not re.search(r"\b\d+\s*(?:min\.?|minutes?)\s+before\b", lower):
        return text

    candidate = text.replace("–", "-").replace("—", "-")
    candidate = re.sub(r"\b(\d{1,2})\.\s*(\d{2})\b", r"\1:\2", candidate)
    token = r"\d{1,2}(?::\d{2})?\s*(?:[AaPp]\.?[Mm]\.?)?"
    range_match = re.search(rf"(?<!\d)({token})\s*-\s*({token})(?!\d)", candidate, flags=re.IGNORECASE)
    if range_match and (":" in range_match.group(0) or re.search(r"[AaPp]\.?[Mm]\.?", range_match.group(0))):
        return range_match.group(0)
    single_match = re.search(r"(?<!\d)(\d{1,2}(?::\d{2})?\s*(?:[AaPp]\.?[Mm]\.?))(?!\d)", candidate, flags=re.IGNORECASE)
    if single_match:
        return single_match.group(1)
    single_24 = re.search(r"(?<!\d)(\d{1,2}:\d{2})(?!\d)", candidate)
    if single_24:
        after = candidate[single_24.end():single_24.end() + 15].lower()
        if "minute" not in after and "min" not in after:
            return single_24.group(1)
    return ""


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

    text = _strip_supplier_warning_time_text(text)
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



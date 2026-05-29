"""Clock-time extraction helpers."""

from __future__ import annotations

import re

from parser_modules.common import clean_space


def find_clock_range(value):
    text = clean_space(value).replace("–", "-").replace("—", "-")
    # Require either a colon or an AM/PM suffix, so ranges like "5-8 minutes"
    # are not interpreted as 5:00 AM - 8:00 AM.
    token = r"\d{1,2}(?::\d{2})?\s*(?:[AaPp]\.?[Mm]\.?)?"
    pattern = re.compile(rf"(?<!\d)({token})\s*-\s*({token})(?!\d)", flags=re.IGNORECASE)
    for match in pattern.finditer(text):
        raw = match.group(0)
        after = text[match.end():match.end() + 15].lower()
        if "minute" in after or "min" in after:
            continue
        if ":" not in raw and not re.search(r"[AaPp]\.?[Mm]\.?", raw):
            continue
        return raw
    return ""


def find_single_clock_time(value):
    text = clean_space(value)
    match = re.search(r"(?<!\d)(\d{1,2}(?::\d{2})?\s*(?:[AaPp]\.?[Mm]\.?))(?!\d)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r"(?<!\d)(\d{1,2}:\d{2})(?!\d)", text)
    if match:
        after = text[match.end():match.end() + 15].lower()
        if "minute" not in after and "min" not in after:
            return match.group(1)
    return ""



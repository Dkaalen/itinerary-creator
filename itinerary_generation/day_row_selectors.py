"""Row text and selection helpers for day planning."""

from __future__ import annotations

import re

from itinerary_generation.common import get_row_type
from shared.text import clean_space


def _text(row: dict) -> str:
    return " ".join(str(row.get(key, "") or "") for key in ["title", "details", "original_title"] if str(row.get(key, "") or "").strip())


def _all_text(rows: list[dict]) -> str:
    return " ".join(_text(row) for row in rows)


def _is_empty_activity(row: dict) -> bool:
    if get_row_type(row) != "Activity":
        return False
    raw = _text(row).strip()
    city = str(row.get("city", "") or "").strip()
    if not raw:
        return True
    cleaned = clean_space(raw).strip(" -:|")
    lower = cleaned.lower()
    if city and lower == city.lower():
        return True
    def _matches_leisure(value: str) -> bool:
        item = clean_space(value).strip(" -:|").lower()
        if not item:
            return False
        pattern = r"spend time at leisure\.?"
        if city:
            pattern = rf"(?:{re.escape(city.lower())}:?\s*)?{pattern}"
        return bool(re.fullmatch(pattern, item) or (city and re.fullmatch(rf"a day at leisure in {re.escape(city.lower())}\.?", item)))

    if any(_matches_leisure(row.get(key, "")) for key in ["title", "original_title", "details"]):
        return True

    leisure_pattern = r"spend time at leisure\.?"
    if city:
        leisure_pattern = rf"(?:{re.escape(city.lower())}:?\s*)?{leisure_pattern}"
    if re.fullmatch(leisure_pattern, lower):
        return True
    return bool(city and re.fullmatch(rf"a day at leisure in {re.escape(city.lower())}\.?", lower))


def _activity_rows(rows: list[dict]) -> list[dict]:
    return [row for row in rows if get_row_type(row) == "Activity" and not _is_empty_activity(row)]


def _has_text(rows: list[dict], *needles: str) -> bool:
    lower = _all_text(rows).lower()
    return any(needle.lower() in lower for needle in needles)

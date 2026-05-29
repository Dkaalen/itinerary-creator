"""Row text and selection helpers for day planning."""

from __future__ import annotations

import re

from itinerary_generation.common import get_row_type


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
    cleaned = re.sub(r"\s+", " ", raw).strip(" -:|")
    return bool(city and cleaned.lower() == city.lower())


def _activity_rows(rows: list[dict]) -> list[dict]:
    return [row for row in rows if get_row_type(row) == "Activity" and not _is_empty_activity(row)]


def _has_text(rows: list[dict], *needles: str) -> bool:
    lower = _all_text(rows).lower()
    return any(needle.lower() in lower for needle in needles)

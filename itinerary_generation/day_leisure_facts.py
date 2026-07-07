"""Leisure/open-time helpers for day facts."""

from __future__ import annotations

from typing import Any, Mapping

from itinerary_generation.common import get_row_type
from itinerary_generation.day_city_facts import row_text, text_value

LEISURE_MARKERS = ("leisure", "free time", "free day", "at your own pace", "open day", "own arrangements")


def is_blank_activity_or_leisure(row: Mapping[str, Any]) -> bool:
    """Return whether a row represents free/open time rather than an arranged activity."""

    row_type = get_row_type(dict(row))
    text = row_text(row).lower()
    if row_type == "Leisure":
        return True
    if row_type != "Activity":
        return False
    return any(marker in text for marker in LEISURE_MARKERS) or not text_value(row.get("title") or row.get("original_title") or row.get("details"))


def has_leisure_markers(text: str) -> bool:
    """Return whether normalized text contains a leisure marker."""

    lower = str(text or "").lower()
    return any(marker in lower for marker in LEISURE_MARKERS)


__all__ = ["LEISURE_MARKERS", "has_leisure_markers", "is_blank_activity_or_leisure"]

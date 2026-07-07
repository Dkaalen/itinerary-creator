"""Leisure/open-time helpers for day facts."""

from __future__ import annotations

from typing import Any, Mapping

from itinerary_generation.common import get_row_type
from itinerary_generation.day_city_facts import row_text, text_value

LEISURE_MARKERS = ("leisure", "free time", "free day", "at your own pace", "open day", "own arrangements")


def _activity_heading_text(row: Mapping[str, Any]) -> str:
    """Return only title-like fields for blank/leisure activity detection."""

    return " ".join(
        str(row.get(key) or "").strip()
        for key in ("title", "original_title")
        if str(row.get(key) or "").strip()
    ).strip()


def is_blank_activity_or_leisure(row: Mapping[str, Any]) -> bool:
    """Return whether a row represents free/open time rather than an arranged activity.

    Supplier activity inclusions can legitimately contain phrases such as
    "2 hours free time in Santa Claus Village".  Those inclusions must not turn
    the whole arranged activity into a leisure row.
    """

    row_type = get_row_type(dict(row))
    text = row_text(row).lower()
    if row_type == "Leisure":
        return True
    if row_type != "Activity":
        return False
    heading_text = _activity_heading_text(row).lower()
    if not text_value(row.get("title") or row.get("original_title") or row.get("details")):
        return True
    if heading_text:
        return any(marker in heading_text for marker in LEISURE_MARKERS)
    return any(marker in text for marker in LEISURE_MARKERS)


def has_leisure_markers(text: str) -> bool:
    """Return whether normalized text contains a leisure marker."""

    lower = str(text or "").lower()
    return any(marker in lower for marker in LEISURE_MARKERS)


__all__ = ["LEISURE_MARKERS", "has_leisure_markers", "is_blank_activity_or_leisure"]

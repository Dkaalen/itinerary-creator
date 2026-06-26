"""Canonical page ordering for preview and PDF rendering."""

from __future__ import annotations

from typing import Any

from itinerary_generation.common import get_day_number
from itinerary_generation.editor_page_contract import final_section_page_id, stable_page_id

_STANDARD_FINAL_SECTION_IDS = {"whats_included", "whats_not_included", "important_travel_notes"}


def _day_sort_key(day: Any) -> tuple[int, str]:
    raw_day = str(getattr(day, "day", "") or getattr(day, "number", "") or "")
    number = get_day_number(raw_day)
    return (number if number is not None else 10_000, raw_day)


def sorted_render_days(days: list[Any] | tuple[Any, ...] | None) -> list[Any]:
    """Return day render objects in numeric itinerary order."""

    return sorted(list(days or []), key=_day_sort_key)


def canonical_render_page_order(render_document: Any) -> list[str]:
    """Return a safe page order that cannot reorder generated itinerary days."""

    page_ids: list[str] = []
    hidden = set(getattr(render_document, "hidden_page_ids", []) or [])

    if getattr(render_document, "cover", None) is not None and "cover" not in hidden:
        page_ids.append("cover")
    if getattr(render_document, "summary", None) is not None and "summary" not in hidden:
        page_ids.append("summary")

    for day in sorted_render_days(getattr(render_document, "days", []) or []):
        page_id = stable_page_id("day", getattr(day, "day", ""))
        if page_id not in hidden:
            page_ids.append(page_id)

    for section in getattr(render_document, "final_sections", []) or []:
        section_id = str(getattr(section, "section_id", "") or "")
        page_id = final_section_page_id(section_id) if section_id in _STANDARD_FINAL_SECTION_IDS else section_id
        if page_id and page_id not in hidden:
            page_ids.append(page_id)

    ordered: list[str] = []
    for page_id in page_ids:
        if page_id and page_id not in ordered:
            ordered.append(page_id)
    return ordered


__all__ = ["canonical_render_page_order", "sorted_render_days"]

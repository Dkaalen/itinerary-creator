"""Canonical page ordering for preview and PDF rendering."""

from __future__ import annotations

from typing import Any

from itinerary_generation.common import get_day_number
from itinerary_generation.editor_page_contract import final_section_page_id, ordered_page_ids, stable_page_id

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


def render_page_order_with_editor_request(render_document: Any, requested_order: list[str] | tuple[str, ...] | None = None) -> list[str]:
    """Return a render page order that respects editor page movement safely.

    The editor owns page visibility and user-requested page placement.  The
    renderer still owns generated itinerary-day ordering, because exporting Day
    2 after Day 5 is never a valid document state.  This helper merges those
    responsibilities: final/custom pages can move around generated days, while
    generated day slots are always filled in canonical day-number order.
    """

    canonical_order = canonical_render_page_order(render_document)
    if not requested_order:
        return canonical_order

    day_ids = [stable_page_id("day", getattr(day, "day", "")) for day in sorted_render_days(getattr(render_document, "days", []) or [])]
    day_ids = [page_id for page_id in day_ids if page_id in canonical_order]
    if not day_ids:
        return ordered_page_ids(canonical_order, requested_order)

    known_requested = ordered_page_ids(canonical_order, requested_order)
    canonical_day_iter = iter(day_ids)
    merged: list[str] = []
    used_days: set[str] = set()
    for page_id in known_requested:
        if page_id in day_ids:
            for canonical_day_id in canonical_day_iter:
                if canonical_day_id not in used_days:
                    merged.append(canonical_day_id)
                    used_days.add(canonical_day_id)
                    break
            continue
        if page_id not in merged:
            merged.append(page_id)

    for page_id in canonical_order:
        if page_id not in merged:
            merged.append(page_id)
    return merged


__all__ = ["canonical_render_page_order", "render_page_order_with_editor_request", "sorted_render_days"]

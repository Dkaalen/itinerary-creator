"""Editable-draft lookup helpers."""

from __future__ import annotations

from typing import Any, Mapping

from itinerary_generation.editable_draft_normalize import _as_text

def section_by_id(editor_draft: Mapping[str, Any], section_id: str) -> dict[str, Any]:
    for section in editor_draft.get("final_sections") or []:
        if isinstance(section, Mapping) and section.get("section_id") == section_id:
            return dict(section)
    return {}


def day_by_id(editor_draft: Mapping[str, Any], day_id: str) -> dict[str, Any]:
    for day in editor_draft.get("days") or []:
        if isinstance(day, Mapping) and str(day.get("day_id") or day.get("day") or "") == str(day_id):
            return dict(day)
    return {}


def first_block_html(day: Mapping[str, Any]) -> str | None:
    blocks = day.get("blocks") if isinstance(day, Mapping) else None
    if not isinstance(blocks, (list, tuple)) or not blocks:
        return None
    block = blocks[0]
    if not isinstance(block, Mapping):
        return None
    return _as_text(block.get("content_html", block.get("html", "")))

__all__ = ["section_by_id", "day_by_id", "first_block_html"]

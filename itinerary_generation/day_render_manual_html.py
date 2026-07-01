"""Resolve manual day-body HTML overrides for typed render documents."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from itinerary_generation.editable_draft import day_by_id
from itinerary_generation.generated_ownership import blocks_html_is_manual


@dataclass(frozen=True, slots=True)
class ManualDayHtml:
    html: str
    is_manual: bool


def _html_from_owner(owner: Mapping[str, Any]) -> str:
    if "blocks_html" in owner:
        return str(owner.get("blocks_html") or "")
    blocks = owner.get("blocks")
    if not isinstance(blocks, (list, tuple)):
        return ""
    fragments = []
    for block in blocks:
        if not isinstance(block, Mapping):
            continue
        fragments.append(str(block.get("content_html", block.get("html", "")) or ""))
    return "".join(fragments)


def manual_day_html_override(day: str, output_edits: Mapping[str, Any] | None) -> ManualDayHtml:
    """Return the saved manual body override for a day, if one exists."""

    if not isinstance(output_edits, Mapping):
        return ManualDayHtml("", False)
    typed_day = day_by_id(output_edits.get("editor_draft", {}) if isinstance(output_edits.get("editor_draft"), Mapping) else {}, day)
    day_edits = (output_edits.get("days") or {}).get(day, {}) if isinstance(output_edits.get("days"), Mapping) else {}
    for owner in (typed_day, day_edits):
        if isinstance(owner, Mapping) and blocks_html_is_manual(owner):
            return ManualDayHtml(_html_from_owner(owner), True)
    return ManualDayHtml("", False)


__all__ = ["ManualDayHtml", "manual_day_html_override"]

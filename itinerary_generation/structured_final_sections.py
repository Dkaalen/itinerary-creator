"""Structured final-section builders."""

from __future__ import annotations

from typing import Iterable

from itinerary_generation.exclusion_sections import create_structured_whats_not_included
from itinerary_generation.structured_inclusions import build_structured_inclusion_sections
from itinerary_generation.structured_model import StructuredListItem, StructuredListSection
from itinerary_generation.structured_rendering import normalize_structured_list_sections

def _split_structured_item(value: str, category: str = "") -> StructuredListItem:
    lines = [line.strip() for line in str(value or "").replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip()]
    if not lines:
        return StructuredListItem(label="", category=category)
    return StructuredListItem(label=lines[0], detail_lines=tuple(lines[1:]), category=category)


def _section_from_mapping(section_id: str, title: str, raw_items: Iterable[str]) -> StructuredListSection | None:
    items = tuple(item for item in (_split_structured_item(value, section_id) for value in raw_items) if item.label)
    if not title or not items:
        return None
    return StructuredListSection(section_id=section_id, title=title, items=items)


def _inclusion_sections(parsed_rows: list[dict], grouped_days: dict[str, list[dict]]) -> tuple[StructuredListSection, ...]:
    return build_structured_inclusion_sections(parsed_rows, grouped_days)


def _exclusion_sections(parsed_rows: list[dict]) -> tuple[StructuredListSection, ...]:
    # Preserve source_row_ids and detail lines from the structured exclusion API.
    # The older string-only adapter is intentionally bypassed here so model
    # validation can audit that self-arranged/optional/excluded rows still have
    # visible What's-not-included coverage.
    return normalize_structured_list_sections(create_structured_whats_not_included(parsed_rows))

__all__ = ["_split_structured_item", "_section_from_mapping", "_inclusion_sections", "_exclusion_sections"]

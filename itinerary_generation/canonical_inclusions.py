"""Canonical inclusion and note helpers."""

from __future__ import annotations

from typing import Iterable

from itinerary_generation.content_engine import is_internal_note_text, sanitize_inclusion_item


def should_hide_note_row(row: dict) -> bool:
    text = f"{row.get('title','')} {row.get('details','')} {row.get('original_title','')}"
    return is_internal_note_text(text)


def canonical_included_items(items: Iterable[str]) -> list[str]:
    clean_items = []
    seen = set()
    for item in (sanitize_inclusion_item(item) for item in items):
        if not item:
            continue
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        clean_items.append(item)
    return clean_items

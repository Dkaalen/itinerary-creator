"""Stable editor page and source-row identifier helpers."""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence


def _slug(value: Any) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    return text or "page"


def stable_page_id(prefix: str, value: Any) -> str:
    return f"{prefix}-{_slug(value)}"


def source_row_ids_for_rows(rows: Sequence[Mapping[str, Any]] | None) -> tuple[str, ...]:
    ids: list[str] = []
    seen: set[str] = set()
    for index, row in enumerate(rows or []):
        if not isinstance(row, Mapping):
            continue
        row_id = str(row.get("row_id") or row.get("source_row_id") or row.get("line_number") or index).strip()
        if row_id and row_id not in seen:
            ids.append(row_id)
            seen.add(row_id)
    return tuple(ids)


def final_section_page_id(section_id: str) -> str:
    mapping = {
        "whats_included": "final-whats-included",
        "whats_not_included": "final-whats-not-included",
        "important_travel_notes": "final-important-travel-notes",
    }
    return mapping.get(str(section_id or ""), stable_page_id("final", section_id))

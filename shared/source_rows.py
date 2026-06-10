"""Neutral source-row identity and source-text helpers.

This module intentionally has no dependency on parser, normalizer, itinerary
rendering, Streamlit, or PDF packages. It is safe for all layers to import.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from shared.text import clean_space, clean_text

SOURCE_TEXT_FIELDS: tuple[str, ...] = (
    "source_text",
    "raw_text",
    "description_raw",
    "original_text",
    "input_text",
    "raw",
    "original_title",
    "title",
    "details",
)

DISPLAY_SOURCE_TEXT_FIELDS: tuple[str, ...] = (
    "title",
    "hotel_name",
    "details",
    "original_title",
)


def source_row_id(row: Mapping[str, Any], fallback_index: int = 0) -> str:
    """Return the stable structured-model source-row id for a row."""

    value = str(row.get("row_id") or "").strip()
    return value or f"generated-row-{fallback_index}"


def edit_row_id(row: Mapping[str, Any], fallback_index: int = 0) -> str:
    """Return the row id used by editable row state and QA reports."""

    value = str(row.get("row_id") or "").strip()
    if value:
        return value
    line_number = row.get("line_number")
    if line_number not in (None, ""):
        return f"line_{line_number}"
    return source_row_id(row, fallback_index)


def source_text(
    row: Mapping[str, Any] | None,
    fields: Iterable[str] = SOURCE_TEXT_FIELDS,
    *,
    separator: str = "\n",
    first_non_empty: bool = False,
    limit: int | None = None,
) -> str:
    """Return supplier/source text using one ordered field policy."""

    if not isinstance(row, Mapping):
        return ""
    parts: list[str] = []
    for field in fields:
        value = row.get(field)
        if value in (None, ""):
            continue
        text = str(value).strip()
        if not text:
            continue
        if first_non_empty:
            parts = [text]
            break
        parts.append(text)
    text = separator.join(parts).strip()
    if limit is not None and len(text) > limit:
        return text[: max(limit - 1, 0)].rstrip() + "…"
    return text


def rows_by_source_id(rows: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    """Return a stable lookup keyed like ``SourceRowRef.row_id``."""

    return {source_row_id(row, index): row for index, row in enumerate(rows or [])}


def row_ids_for_rows(rows: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    """Return source-row ids for rows in their current order."""

    return tuple(source_row_id(row, index) for index, row in enumerate(rows or []))

"""Neutral source-row identity and source-text helpers.

This module intentionally has no dependency on parser, normalizer, itinerary
rendering, Streamlit, or PDF packages. It is safe for all layers to import.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from hashlib import sha256
import json
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


_SOURCE_ID_FIELDS: tuple[str, ...] = (
    "line_number",
    "day",
    "type",
    "source_type",
    "effective_type",
    "start_date",
    "end_date",
    "city",
    "raw",
    "original_title",
    "title",
    "details",
    "hotel_name",
)


def _stable_identity_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _stable_identity_value(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (list, tuple, set, frozenset)):
        items = [_stable_identity_value(item) for item in value]
        return sorted(items, key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, default=str)) if isinstance(value, (set, frozenset)) else items
    if isinstance(value, str):
        return clean_space(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return clean_space(str(value))


def source_row_id(row: Mapping[str, Any], fallback_index: int = 0) -> str:
    """Return an order-independent structured-model source-row id.

    Real parser rows keep their supplier-backed ``row_id``. Synthetic or
    legacy rows use a deterministic content fingerprint so regrouping or
    filtering cannot silently change their identity. ``fallback_index`` is
    retained for API compatibility but is intentionally not part of the id.
    """

    _ = fallback_index
    value = str(row.get("row_id") or "").strip()
    if value:
        return value
    payload = {
        field: _stable_identity_value(row.get(field))
        for field in _SOURCE_ID_FIELDS
        if row.get(field) not in (None, "", [], (), {})
    }
    if not payload:
        payload = {"empty": True}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return f"generated-row-{sha256(encoded.encode('utf-8')).hexdigest()[:16]}"


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


def _unique_source_ids(rows: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    counts: dict[str, int] = {}
    result: list[str] = []
    for index, row in enumerate(rows or []):
        base = source_row_id(row, index)
        counts[base] = counts.get(base, 0) + 1
        result.append(base if counts[base] == 1 else f"{base}-duplicate-{counts[base]}")
    return tuple(result)


def rows_by_source_id(rows: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    """Return a stable lookup without overwriting identical legacy rows."""

    row_list = tuple(rows or ())
    return dict(zip(_unique_source_ids(row_list), row_list))


def row_ids_for_rows(rows: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    """Return stable, collision-safe source-row ids in current display order."""

    return _unique_source_ids(tuple(rows or ()))

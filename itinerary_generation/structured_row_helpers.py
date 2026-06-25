"""Shared row helpers for structured itinerary document builders."""

from __future__ import annotations

from itinerary_generation.common import get_row_type
from shared.source_rows import clean_text, source_row_id, source_text
from itinerary_generation.structured_model import SourceRowRef

_ACTIVITY_STRUCTURE_MARKERS = (
    "|",
    "what's included",
    "whats included",
    "meeting point",
    "pick up / meeting point",
    "pickup / meeting point",
    "pick-up/drop-off",
    "duration",
)


def _has_structured_activity_supplier_text(source_lower: str) -> bool:
    return sum(1 for marker in _ACTIVITY_STRUCTURE_MARKERS if marker in source_lower) >= 2


def _clean(value: object) -> str:
    return clean_text(value)


def _row_id(row: dict, fallback_index: int = 0) -> str:
    return source_row_id(row, fallback_index)


def _source_text(row: dict) -> str:
    return source_text(row, ("raw", "original_title", "title", "details"))


def _source_ref(row: dict, fallback_index: int) -> SourceRowRef:
    return SourceRowRef(
        row_id=_row_id(row, fallback_index),
        line_number=row.get("line_number") if isinstance(row.get("line_number"), int) else None,
        day=str(row.get("day", "") or ""),
        source_type=str(row.get("source_type") or row.get("type") or ""),
        effective_type=str(get_row_type(row) or ""),
        start_date=str(row.get("start_date", "") or ""),
        end_date=str(row.get("end_date", "") or ""),
        city=str(row.get("city", "") or ""),
        raw_text=str(row.get("raw") or row.get("details") or row.get("title") or ""),
        title=str(row.get("title", "") or ""),
        original_title=str(row.get("original_title", "") or ""),
        commercial_status=str(row.get("commercial_status") or ("optional" if row.get("is_optional") else "included")),
        commercial_reason=str(row.get("commercial_reason", "") or ""),
    )

__all__ = [
    "_ACTIVITY_STRUCTURE_MARKERS",
    "_has_structured_activity_supplier_text",
    "_clean",
    "_row_id",
    "_source_text",
    "_source_ref",
]

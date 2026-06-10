"""Shared helpers for canonical itinerary builders."""

from __future__ import annotations

import re
from typing import Iterable

from shared.source_rows import clean_text, source_row_id, source_text
from itinerary_generation.content_engine import group_tour_pickup_window_from_overview


def _clean(value: object) -> str:
    return clean_text(value)


def _row_id(row: dict) -> str:
    return source_row_id(row, 0) if row.get("row_id") else ""


def _is_fløibanen(title: str) -> bool:
    lower = title.lower()
    return "fløibanen" in lower or "floibanen" in lower


def _group_tour_pickup_window(rows: Iterable[dict]) -> str:
    for row in rows:
        value = group_tour_pickup_window_from_overview(row)
        if value:
            return value
    return ""


def _source_text(row: dict) -> str:
    return source_text(row, ("title", "hotel_name", "details", "original_title"), separator=" ")

"""Shared helpers for canonical itinerary builders."""

from __future__ import annotations

import re
from typing import Iterable

from itinerary_generation.content_engine import group_tour_pickup_window_from_overview


def _clean(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _row_id(row: dict) -> str:
    return str(row.get("row_id") or "")


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
    return " ".join(str(row.get(key) or "") for key in ("title", "hotel_name", "details", "original_title"))

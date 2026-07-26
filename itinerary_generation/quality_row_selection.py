"""Canonical row selection for itinerary quality and health reporting.

This module owns only row normalization and important-row classification. Rule
engines, rating calculation, and report formatting consume its results rather
than reimplementing selection semantics.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from itinerary_generation.row_filters import get_row_type

IMPORTANT_ROW_TYPES = frozenset(
    {
        "Hotel",
        "Activity",
        "Transfer",
        "Train",
        "Flight",
        "Cruise",
        "Ferry",
        "Transport",
        "Arrival",
        "Departure",
        "Day Overview",
    }
)


def as_quality_rows(rows: Iterable[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Return mutable row dictionaries accepted by quality contracts."""

    return [row for row in rows or () if isinstance(row, dict)]


def is_important_quality_row(row: dict[str, Any]) -> bool:
    """Return whether a row participates in itinerary quality decisions."""

    row_type = get_row_type(row)
    raw_type = row.get("type", "")
    return row_type in IMPORTANT_ROW_TYPES or raw_type in IMPORTANT_ROW_TYPES


def select_important_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return important rows in source order without copying or deduplicating."""

    return [row for row in rows if is_important_quality_row(row)]


__all__ = [
    "IMPORTANT_ROW_TYPES",
    "as_quality_rows",
    "is_important_quality_row",
    "select_important_rows",
]

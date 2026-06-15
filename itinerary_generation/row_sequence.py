"""Stable ordering helpers for itinerary row collections."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def ordered_cities(rows: Iterable[Mapping[str, Any]]) -> tuple[str, ...]:
    """Return non-empty row cities once, preserving their first-seen order."""

    cities: list[str] = []
    seen: set[str] = set()
    for row in rows:
        city = str(row.get("city", "")).strip()
        if city and city not in seen:
            seen.add(city)
            cities.append(city)
    return tuple(cities)

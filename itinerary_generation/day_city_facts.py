"""City extraction helpers for day facts.

This module owns destination/city normalization only. It must stay prose-free.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from itinerary_generation.destination_validation import is_valid_destination_city
from itinerary_generation.transport_safety import base_destination_from_terminal
from place_aliases import canonicalize_place_name
from shared.text import clean_space
from text_polish import polish_title


def text_value(value: object) -> str:
    """Return normalized one-line text."""

    return clean_space(value)


def row_text(row: Mapping[str, Any]) -> str:
    """Return the searchable text for one itinerary row."""

    return text_value(
        " ".join(
            str(row.get(key, "") or "")
            for key in (
                "type",
                "effective_type",
                "city",
                "title",
                "original_title",
                "details",
                "description",
                "meeting_point",
                "end_point",
                "hotel_name",
                "room_category",
            )
        )
    )


def canonical_city(value: object) -> str:
    """Return a clean destination city or an empty string if it is not safe."""

    raw = text_value(value)
    if not raw:
        return ""
    raw = base_destination_from_terminal(raw) or raw
    raw = re.sub(
        r"\s+(?:central\s+station|railway\s+station|train\s+station|bus\s+station|airport|ferry\s+terminal|cruise\s+terminal|terminal|harbou?r|port)$",
        "",
        raw,
        flags=re.IGNORECASE,
    ).strip(" -:|.,")
    city = polish_title(canonicalize_place_name(raw) or raw)
    if not city or not is_valid_destination_city(city):
        return ""
    return city


def add_unique_city(items: list[str], value: object) -> None:
    """Append a canonical city once."""

    city = canonical_city(value)
    if city and city not in items:
        items.append(city)


def city_from_arrival_departure_text(row: Mapping[str, Any], *, direction: str) -> str:
    """Extract an arrival/departure city from row text when no city field exists."""

    text = row_text(row)
    patterns = (
        r"\barrival\s+(?:in|at|to)\s+([^,|:;.-]+)",
        r"\barrive\s+(?:in|at|to)\s+([^,|:;.-]+)",
    ) if direction == "arrival" else (
        r"\bdeparture\s+(?:from|in|at)\s+([^,|:;.-]+)",
        r"\bdepart\s+(?:from|in|at)\s+([^,|:;.-]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        phrase = match.group(1).strip(" -:|.,")
        phrase = re.split(r"\b(?:arrival|arrive|departure|depart)\b", phrase, maxsplit=1, flags=re.IGNORECASE)[0].strip(" -:|.,")
        words = [word for word in phrase.split() if word]
        for size in range(min(3, len(words)), 0, -1):
            city = canonical_city(" ".join(words[:size]))
            if city:
                return city
    return ""


def arrival_departure_city(
    rows: Sequence[Mapping[str, Any]],
    row_type: str,
    *,
    direction: str,
    primary_city: str,
    route_origins: Sequence[str] = (),
) -> str:
    """Return the safest explicit arrival/departure city for a day."""

    from itinerary_generation.common import get_row_type

    for row in rows:
        if get_row_type(dict(row)) != row_type:
            continue
        detected = canonical_city(row.get("city", "")) or city_from_arrival_departure_text(row, direction=direction)
        if detected:
            return detected
        if direction == "arrival" and route_origins:
            return route_origins[0]
        return primary_city
    return ""


__all__ = [
    "add_unique_city",
    "arrival_departure_city",
    "canonical_city",
    "city_from_arrival_departure_text",
    "row_text",
    "text_value",
]

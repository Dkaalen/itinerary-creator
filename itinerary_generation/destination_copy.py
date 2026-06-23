"""Destination-specific deterministic copy helpers.

These helpers keep generic fallback copy out of client-facing proposal text while
remaining fact-safe.  They do not add activities or change itinerary facts; they
only provide city-specific colour for summary/leisure wording when the source
row is intentionally light.
"""

from __future__ import annotations

import re
from typing import Iterable, Sequence

from text_polish import polish_title


CITY_ARC_FALLBACKS: dict[str, str] = {
    "oslo": "Discover the Norwegian capital",
    "kristiansand": "Southern coastal charm",
    "stavanger": "Stavanger harbour and fjord gateway",
    "bergen": "Bergen harbour and mountain views",
    "copenhagen": "Copenhagen design and harbour life",
    "stockholm": "Stockholm islands and old town",
    "gothenburg": "Gothenburg canals and coastal culture",
    "helsinki": "Helsinki design and waterfront life",
    "reykjavík": "Reykjavík culture and coastal colour",
    "reykjavik": "Reykjavík culture and coastal colour",
    "tromsø": "Arctic city and northern landscapes",
    "tromso": "Arctic city and northern landscapes",
    "alta": "Arctic nature and Northern Lights country",
    "rovaniemi": "Lapland forest and Arctic Circle atmosphere",
}

CITY_LEISURE_SUGGESTIONS: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "oslo": (
        ("the waterfront", ("fjord sightseeing", "oslofjord", "fjord cruise")),
        ("neighbourhood cafés", ("food tour", "culinary", "tasting")),
        ("the city’s museums and galleries", ("museum", "vasa")),
        ("a first impression of the Norwegian capital", ("welcome to norway",)),
    ),
    "kristiansand": (
        ("the harbourfront", ("harbour", "harbor")),
        ("southern coastal atmosphere", ("coastal charm",)),
        ("cafés and old town streets", ("walking tour",)),
        ("an easy pace by the sea", ("kayak", "kayaking", "otra river")),
    ),
    "stavanger": (
        ("the harbourfront", ("harbour", "harbor")),
        ("old wooden streets", ("walking tour",)),
        ("cafés around the centre", ("food", "culinary", "tasting")),
        ("the city’s coastal atmosphere", ("lysefjord", "preikestolen", "pulpit rock")),
    ),
    "bergen": (
        ("the harbourfront", ("harbour", "cruise transfer")),
        ("colourful lanes around the centre", ("walking tour", "bergen past")),
        ("cafés and local shops", ("food", "culinary", "tasting")),
        ("views between the city and surrounding mountains", ("fløy", "floy", "funicular", "fløibanen", "floibanen")),
    ),
    "copenhagen": (
        ("harbourfront neighbourhoods", ("harbour",)),
        ("design shops and cafés", ("design", "food")),
        ("historic streets at an easy pace", ("walking tour", "old town")),
    ),
    "stockholm": (
        ("waterfront viewpoints", ("boat", "cruise")),
        ("island neighbourhoods", ("archipelago",)),
        ("cafés and old town streets", ("old town", "walking")),
    ),
    "helsinki": (
        ("waterfront neighbourhoods", ("ferry", "harbour")),
        ("design shops and cafés", ("design", "food")),
        ("the city centre at an easy pace", ("walking tour",)),
    ),
}


def _normalise_city(city: object) -> str:
    return re.sub(r"\s+", " ", str(city or "").strip()).lower()


def _rows_text(rows: Iterable[dict] | None) -> str:
    return " ".join(
        " ".join(
            str(row.get(key, "") or "")
            for key in ("city", "title", "original_title", "details", "description")
        )
        for row in rows or []
        if isinstance(row, dict)
    ).lower()


def destination_arc_fallback(city: object) -> str:
    """Return city-specific Journey Arc fallback copy when real highlights are absent."""

    city_key = _normalise_city(city)
    if city_key in CITY_ARC_FALLBACKS:
        return CITY_ARC_FALLBACKS[city_key]
    city_name = polish_title(str(city or "").strip())
    return f"Discover {city_name}" if city_name else "Time to explore at your own pace"


def leisure_description(city: object, rows: Sequence[dict] | Iterable[dict] | None = None) -> str:
    """Return premium free-time copy without repeating already-covered experiences."""

    city_name = polish_title(str(city or "").strip())
    city_key = _normalise_city(city_name)
    context = _rows_text(rows)
    suggestions = CITY_LEISURE_SUGGESTIONS.get(city_key, ())
    chosen: list[str] = []
    for phrase, covered_markers in suggestions:
        if any(marker in context for marker in covered_markers):
            continue
        if phrase not in chosen:
            chosen.append(phrase)
        if len(chosen) >= 3:
            break

    if not chosen:
        chosen = ["local cafés", "neighbourhoods", "time to settle into the day"]

    if city_name:
        if len(chosen) == 1:
            focus = chosen[0]
        elif len(chosen) == 2:
            focus = f"{chosen[0]} and {chosen[1]}"
        else:
            focus = f"{chosen[0]}, {chosen[1]} or {chosen[2]}"
        return f"Use the remaining time in {city_name} at your own pace, with room for {focus}."
    return "Use the remaining time at your own pace, with room to relax, explore independently or settle into the day."

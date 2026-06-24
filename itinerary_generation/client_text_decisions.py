"""Shared meaning-based decisions for client-facing itinerary text.

This module keeps the small wording decisions used by day intros, Journey Arc,
and late output validation in one place.  The goal is not to generate prose from
random phrases, but to make the same context decision everywhere:

* meaningful activity context wins over logistics;
* destination-only travel/check-in days become ``Welcome to <destination>``;
* real scenic routes may describe the route;
* generic connection/filler wording is never considered a valid experience.
"""

from __future__ import annotations

import re
from typing import Iterable, Sequence

from itinerary_generation.common import get_primary_city, get_row_type, has_hotel
from itinerary_generation.copy.activity_composition import client_activity_intro, client_group_tour_intro


def _normalise_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _contains(text: str, *markers: str) -> bool:
    return any(marker in text for marker in markers)


WEAK_JOURNEY_ARC_RE = re.compile(
    r"(?:"
    r"\bflight\s+connection\b|"
    r"\b(?:scenic\s+)?travel\s+connection\b|"
    r"\bonward\s+(?:flight|train|travel|connection|connections)\b|"
    r"\btravel\s+arrangements\b|"
    r"\baccommodation\s+as\s+listed\b|"
    r"\barrival\s+arrangements\b|"
    r"\btravel\s+continues\b|"
    r"\bcontinue\s+your\s+journey\s+with\s+arranged\s+travel\b"
    r")",
    flags=re.IGNORECASE,
)


SCENIC_ROUTE_MARKERS = (
    "norway in a nutshell",
    "flåm",
    "flam",
    "nærøyfjord",
    "naeroyfjord",
    "bergen railway",
    "flåm railway",
    "flam railway",
    "scenic rail",
    "fjord cruise",
    "coastal cruise",
)


def welcome_arc_phrase(chapter: str = "") -> str:
    chapter = _normalise_text(chapter)
    if chapter and chapter.lower() not in {"journey", "cruise", "route"}:
        return f"Welcome to {chapter}"
    return "Arrival and time to settle in"


def is_weak_journey_arc_phrase(text: object) -> bool:
    value = _normalise_text(text)
    return not value or bool(WEAK_JOURNEY_ARC_RE.search(value))


def sanitize_journey_arc_phrase(text: object, *, chapter: str = "") -> str:
    """Clean stale or generated weak Journey Arc copy.

    This is used by summaries, render/PDF output, the visual editor, and the
    quality gate so those paths cannot drift into different wording standards.
    """

    value = _normalise_text(text)
    if not value:
        return welcome_arc_phrase(chapter) if chapter else "Time to explore at your own pace"
    value = re.sub(r"\bAurora\b", "Northern Lights", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+(?:and|&)\s+onward\s+(?:train|flight|travel|connections?)\b.*$", "", value, flags=re.IGNORECASE).strip(" ,")
    value = re.sub(r"\bonward\s+(?:train|flight|travel|connections?)\b", "", value, flags=re.IGNORECASE).strip(" ,")
    value = _normalise_text(value).strip(" ,")
    if is_weak_journey_arc_phrase(value):
        return welcome_arc_phrase(chapter)
    return value or welcome_arc_phrase(chapter)


def is_scenic_route_text(text: object) -> bool:
    value = str(text or "").lower()
    return _contains(value, *SCENIC_ROUTE_MARKERS)


def _rows_text(rows: Iterable[dict]) -> str:
    return " ".join(
        " ".join(
            [
                str(row.get("city", "")),
                str(row.get("title", "")),
                str(row.get("original_title", "")),
                str(row.get("details", "")),
                " ".join(row.get("includes", []) or []),
            ]
        )
        for row in rows or []
        if isinstance(row, dict)
    ).lower()


def has_meaningful_activity(rows: Iterable[dict]) -> bool:
    return any(
        get_row_type(row) == "Activity" and (row.get("effective_type") or row.get("type")) == "Activity"
        for row in rows or []
    )


def is_destination_logistics_only(rows: Sequence[dict] | Iterable[dict]) -> bool:
    row_list = [row for row in rows or [] if isinstance(row, dict)]
    if not row_list:
        return False
    if has_meaningful_activity(row_list):
        return False
    row_types = {get_row_type(row) for row in row_list}
    if not row_types:
        return False
    logistics_types = {"Hotel", "Transfer", "Flight", "Train", "Transport", "Cruise", "Ferry", "Arrival", "Departure"}
    return row_types.issubset(logistics_types) and (has_hotel(row_list) or "Arrival" in row_types or "Departure" in row_types)


def destination_logistics_phrase(rows: Sequence[dict] | Iterable[dict], *, chapter: str = "") -> str:
    row_list = [row for row in rows or [] if isinstance(row, dict)]
    city = _normalise_text(chapter) or _normalise_text(get_primary_city(row_list))
    row_types = {get_row_type(row) for row in row_list}
    text = _rows_text(row_list)

    if "Departure" in row_types and city:
        return f"Departure from {city}"
    if city and (_contains(text, "northern light village", "panorama suite")):
        return "Northern Lights village stay"
    if city:
        return welcome_arc_phrase(city)
    if is_scenic_route_text(text) or row_types.intersection({"Train", "Transport", "Cruise", "Ferry"}):
        return "Scenic route day"
    return "Arrival and time to settle in"


def choose_journey_arc_phrase(candidates: Sequence[str], *, chapter: str = "") -> str:
    """Pick a compact, cleaned Journey Arc phrase from ordered candidates."""

    cleaned: list[str] = []
    for phrase in candidates:
        value = sanitize_journey_arc_phrase(phrase, chapter=chapter)
        if value and value not in cleaned:
            cleaned.append(value)
    if not cleaned:
        cleaned = [welcome_arc_phrase(chapter)]
    for phrase in cleaned:
        if len(phrase) <= 48:
            return phrase[:1].upper() + phrase[1:]
    phrase = cleaned[0]
    lower = phrase.lower()
    if "northern lights" in lower and ("sámi" in lower or "sami" in lower):
        return "Northern Lights and Sámi culture"
    if "santa village" in lower and "northern lights" in lower:
        return "Northern Lights and Santa Village"
    words = phrase.split()
    shortened = ""
    for word in words:
        candidate = f"{shortened} {word}".strip()
        if len(candidate) > 48:
            break
        shortened = candidate
    return (shortened or phrase[:48].rstrip(" ,"))[:1].upper() + (shortened or phrase[:48].rstrip(" ,"))[1:]

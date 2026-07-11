"""Keep journey-overview chapters distinct without inventing new facts."""

from __future__ import annotations

from typing import Mapping, Sequence

from itinerary_generation.common import get_row_type
from text_polish import polish_title


def _clean(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _activity_title(rows: Sequence[Mapping[str, object]]) -> str:
    for row in rows:
        if get_row_type(dict(row)) != "Activity":
            continue
        title = polish_title(_clean(row.get("display_title") or row.get("title") or row.get("original_title")))
        if title:
            return title
    return ""


def _compact_activity_title(rows: Sequence[Mapping[str, object]], chapter: str) -> str:
    title = _activity_title(rows)
    if not title:
        return ""
    if len(title) <= 48:
        return title

    source = " ".join(
        _clean(value)
        for row in rows
        for value in (row.get("title", ""), row.get("original_title", ""), row.get("details", ""))
    ).casefold()
    if "northern lights" in source or "aurora" in source:
        return "Northern Lights experience"
    if "whale" in source:
        return "Whale watching experience"
    if "fjord" in source or "cruise" in source:
        return "Fjord and coastal scenery"
    return f"Arranged experiences in {chapter}" if chapter else "Arranged experiences"


def distinct_chapter_experience(
    rows: Sequence[Mapping[str, object]],
    chapter: str,
    proposed: str,
    *,
    used: set[str],
    seen_chapters: set[str],
) -> str:
    """Return source-backed wording that is not a duplicate chapter label."""

    phrase = _clean(proposed)
    key = phrase.casefold()
    chapter_key = _clean(chapter).casefold()
    if phrase and key not in used:
        used.add(key)
        seen_chapters.add(chapter_key)
        return phrase

    row_types = {get_row_type(dict(row)) for row in rows}
    if chapter_key in seen_chapters and chapter:
        alternatives = [f"Return to {chapter}"]
    else:
        alternatives = []
    activity = _compact_activity_title(rows, chapter)
    if activity:
        alternatives.append(activity)
    if "Arrival" in row_types:
        alternatives.append(f"Welcome to {chapter}" if chapter else "Arrival and time to settle in")
    if "Leisure" in row_types:
        alternatives.append(f"Independent time in {chapter}" if chapter else "Independent time")
    if "Hotel" in row_types:
        alternatives.append(f"Stay in {chapter}" if chapter else "Accommodation as listed")
    if row_types.intersection({"Train", "Transport", "Cruise", "Ferry", "Flight", "Coach", "Bus", "Transfer"}):
        alternatives.append(f"Travel to {chapter}" if chapter else "Scenic route day")
    alternatives.append(f"Time in {chapter}" if chapter else "Journey arrangements")

    for alternative in alternatives:
        candidate = _clean(alternative)
        if candidate and candidate.casefold() not in used:
            used.add(candidate.casefold())
            seen_chapters.add(chapter_key)
            return candidate
    seen_chapters.add(chapter_key)
    return phrase or (f"Time in {chapter}" if chapter else "Journey arrangements")


__all__ = ["distinct_chapter_experience"]

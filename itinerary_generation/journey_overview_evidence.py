"""Source-evidence rules for journey-overview chapters.

The Journey Overview Brain may summarize itinerary facts, but it must never add
attractions or themes that are not supported by the source rows.  This module
owns chapter destination selection and the final evidence guard.
"""

from __future__ import annotations

import re
from typing import Mapping, Sequence

from itinerary_generation.common import get_row_type
from itinerary_generation.day_facts import build_day_facts
from itinerary_generation.nutshell_domain import has_nutshell_journey
from itinerary_generation.summaries_experience import describe_city_experience
from text_polish import polish_title


def _clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def chapter_source_text(rows: Sequence[Mapping[str, object]]) -> str:
    return " ".join(
        _clean(value)
        for row in rows
        for value in (
            row.get("city", ""),
            row.get("title", ""),
            row.get("original_title", ""),
            row.get("details", ""),
            " ".join(_clean(item) for item in row.get("includes", []) or ()),
        )
        if _clean(value)
    )


def chapter_destination(rows: Sequence[Mapping[str, object]]) -> str:
    """Return the destination chapter owned by the day facts.

    Overnight/accommodation destination beats an activity pickup city.  This
    keeps route-arrival days (for example Bergen→Oslo) in the Oslo chapter.
    """

    facts = build_day_facts(rows)
    # A day excursion followed by overnight transport still belongs to the
    # departure/base-city chapter.  The route endpoint starts its chapter on
    # the following day when the traveller actually arrives and stays there.
    if facts.has_activity and facts.has_overnight_transport and facts.activity_cities:
        return polish_title(facts.activity_cities[0])
    return polish_title(
        facts.overnight_city
        or facts.end_city
        or facts.main_city
        or facts.route_destination
        or facts.start_city
        or "Journey"
    )


_REQUIRED_EVIDENCE: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("vasa museum", ("vasa",)),
    ("blue lagoon", ("blue lagoon",)),
    ("golden circle", ("golden circle", "thingvellir", "þingvellir", "gullfoss", "strokkur")),
    ("snæfellsnes", ("snæfellsnes", "snaefellsnes", "kirkjufell")),
    ("jökulsárlón", ("jökulsárlón", "jokulsarlon", "glacier lagoon")),
    ("northern lights", ("northern light", "aurora")),
    ("sámi", ("sámi", "sami")),
    ("whale", ("whale",)),
    ("fløibanen", ("fløibanen", "floibanen", "fløyen", "floyen")),
    ("food", ("food tour", "tasting", "culinary", "smørrebrød", "smorrebrod")),
)


def _phrase_is_supported(phrase: str, source: str) -> bool:
    phrase_l = phrase.casefold()
    source_l = source.casefold()
    for phrase_marker, evidence_markers in _REQUIRED_EVIDENCE:
        if phrase_marker in phrase_l and not any(marker in source_l for marker in evidence_markers):
            return False
    return True


def _source_backed_fallback(rows: Sequence[Mapping[str, object]], chapter: str) -> str:
    source = chapter_source_text(rows).casefold()
    row_types = {get_row_type(dict(row)) for row in rows}
    if "Departure" in row_types:
        return f"Departure from {chapter}" if chapter else "Departure arrangements"
    if has_nutshell_journey([dict(row) for row in rows]) or "norway in a nutshell" in source:
        return "Norway in a Nutshell and scenic rail"
    activity_titles = [
        polish_title(_clean(row.get("display_title") or row.get("title") or row.get("original_title")))
        for row in rows
        if get_row_type(dict(row)) == "Activity"
        and _clean(row.get("title") or row.get("original_title"))
    ]
    if activity_titles:
        first = activity_titles[0]
        return first if len(first) <= 52 else f"Arranged experiences in {chapter}"
    if "Arrival" in row_types:
        return f"Welcome to {chapter}" if chapter else "Arrival and time to settle in"
    if "Leisure" in row_types:
        return f"Independent time in {chapter}" if chapter else "Independent time"
    if row_types.intersection({"Train", "Transport", "Cruise", "Ferry", "Flight", "Coach", "Bus"}):
        return f"Travel to {chapter}" if chapter else "Scenic route day"
    return f"Stay in {chapter}" if chapter else "Journey arrangements"


def chapter_experience(rows: Sequence[Mapping[str, object]], chapter: str) -> str:
    """Return a compact source-backed chapter summary."""

    source = chapter_source_text(rows)
    source_l = source.casefold()
    has_nutshell = has_nutshell_journey([dict(row) for row in rows]) or "norway in a nutshell" in source_l
    has_food = any(marker in source_l for marker in ("food tour", "tasting", "culinary", "smørrebrød", "smorrebrod"))
    if "tallinn" in source_l and "old town" in source_l:
        return "Tallinn Old Town day trip"
    if has_nutshell and has_food:
        return "Norway in a Nutshell and Oslo food tour" if chapter.casefold() == "oslo" else "Norway in a Nutshell and local food tour"
    if has_nutshell:
        chapter_l = chapter.casefold()
        if chapter_l == "flåm" and any(marker in source_l for marker in ("myrdal", "flåm railway", "flam railway")):
            return "Scenic rail journey to Flåm"
        if chapter_l == "bergen" and any(marker in source_l for marker in ("nærøyfjord", "naeroyfjord", "gudvangen", "fjord cruise")):
            return "Fjord cruise and rail to Bergen"
        return "Norway in a Nutshell and scenic rail"

    phrase = describe_city_experience([dict(row) for row in rows])
    if phrase and _phrase_is_supported(phrase, source):
        return phrase
    return _source_backed_fallback(rows, chapter)


__all__ = [
    "chapter_destination",
    "chapter_experience",
    "chapter_source_text",
]

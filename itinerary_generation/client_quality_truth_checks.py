"""Cross-layer truth checks for the final client render document.

These checks do not generate copy.  They verify that separately rendered title,
intro, activity, leisure, and journey-overview decisions still agree and that
summary facts are supported by the rendered itinerary.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

from itinerary_generation.generation_quality_gate import BLOCKING, ItineraryValidationIssue
from itinerary_generation.schedule_time_ranges import parse_time_range

_INTERNAL_COPY_RE = re.compile(
    r"\b(?:raw supplier notes?|internal fallback|developer(?:-| )only|implementation detail|debug output)\b",
    re.IGNORECASE,
)
_FALSE_OPEN_TIME_RE = re.compile(
    r"\b(?:rest of the day|schedule stays light|day remains light|time .* open|easy and flexible)\b",
    re.IGNORECASE,
)
_CONSTRAINED_TIME_RE = re.compile(
    r"\b(?:no additional plans|practical around dinner and rest|occupies most of the day|until the confirmed activity timing)\b",
    re.IGNORECASE,
)
_RETURN_RE = re.compile(r"\b(?:return to|back in)\s+(.+?)(?:[.,]|$)", re.IGNORECASE)
_WORD_RE = re.compile(r"[a-zA-ZÀ-ÖØ-öø-ÿ]{4,}")
_STOP_WORDS = {
    "with", "from", "your", "today", "tour", "private", "guided", "experience",
    "full", "half", "ticket", "admission", "transfer", "return", "best", "highlights",
}
_SUPPORTED_ENTITY_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("vasa", ("vasa",)),
    ("blue lagoon", ("blue lagoon",)),
    ("golden circle", ("golden circle", "thingvellir", "þingvellir", "gullfoss", "strokkur")),
    ("snæfellsnes", ("snæfellsnes", "snaefellsnes", "kirkjufell")),
    ("jökulsárlón", ("jökulsárlón", "jokulsarlon", "glacier lagoon")),
    ("northern lights", ("northern lights", "aurora")),
    ("sámi", ("sámi", "sami")),
    ("whale", ("whale",)),
    ("fløibanen", ("fløibanen", "floibanen", "fløyen", "floyen")),
)


def _text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _day_body(day: Any) -> str:
    parts = [_text(getattr(day, "title", "")), _text(getattr(day, "intro", ""))]
    for block in getattr(day, "blocks", []) or []:
        parts.extend((_text(getattr(block, "title", "")), _text(getattr(block, "description", ""))))
        parts.extend(_text(item) for item in getattr(block, "includes", []) or [])
        parts.extend(_text(item) for item in getattr(block, "lines", []) or [])
        for meta in getattr(block, "meta", []) or []:
            parts.append(_text(getattr(meta, "value", "")))
    return " ".join(part for part in parts if part)


def _leisure_text(day: Any) -> str:
    return " ".join(
        _text(getattr(block, "description", ""))
        for block in getattr(day, "blocks", []) or []
        if _text(getattr(block, "kind", "")).casefold() in {"leisure", "cruise_leisure"}
    )


def _activity_blocks(day: Any) -> list[Any]:
    return [block for block in getattr(day, "blocks", []) or [] if _text(getattr(block, "kind", "")).casefold() == "activity"]


def _time_ranges(day: Any):
    for block in _activity_blocks(day):
        for meta in getattr(block, "meta", []) or []:
            if "time" not in _text(getattr(meta, "label", "")).casefold():
                continue
            parsed = parse_time_range(getattr(meta, "value", ""))
            if parsed.start_minutes is not None:
                yield parsed


def _meaningful_tokens(value: str) -> set[str]:
    return {word.casefold() for word in _WORD_RE.findall(value) if word.casefold() not in _STOP_WORDS}


def _title_consistency_issues(day: Any) -> Iterable[ItineraryValidationIssue]:
    activities = _activity_blocks(day)
    other_kinds = {
        _text(getattr(block, "kind", "")).casefold()
        for block in getattr(day, "blocks", []) or []
        if _text(getattr(block, "kind", "")).casefold() not in {"activity", "leisure"}
    }
    if len(activities) != 1 or other_kinds.intersection({"travel", "travel_sequence", "accommodation", "group_tour_day"}):
        return ()
    day_title = _text(getattr(day, "title", ""))
    activity_title = _text(getattr(activities[0], "title", ""))
    if not day_title or not activity_title:
        return ()
    day_tokens = _meaningful_tokens(day_title)
    activity_tokens = _meaningful_tokens(activity_title)
    if day_tokens and activity_tokens and not day_tokens.intersection(activity_tokens):
        return (
            ItineraryValidationIssue(
                BLOCKING,
                "day_activity_title_disagreement",
                "Day title and the single rendered activity disagree about product identity.",
                context=f"{getattr(day, 'day', '')}: {day_title} <> {activity_title}",
            ),
        )
    return ()


def client_truth_issues(document: Any) -> list[ItineraryValidationIssue]:
    issues: list[ItineraryValidationIssue] = []
    days = list(getattr(document, "days", []) or [])
    full_body = " ".join(_day_body(day) for day in days)

    if _INTERNAL_COPY_RE.search(full_body):
        issues.append(ItineraryValidationIssue(BLOCKING, "internal_copy_leak", "Internal/developer wording leaked into client-facing output."))

    seen_cities: set[str] = set()
    for day in days:
        day_id = _text(getattr(day, "day", ""))
        city = _text(getattr(day, "city", ""))
        intro = _text(getattr(day, "intro", ""))
        leisure = _leisure_text(day)
        if intro and leisure and intro.casefold() == leisure.casefold():
            issues.append(ItineraryValidationIssue(BLOCKING, "duplicate_intro_and_leisure", "Day intro and free-time copy are identical.", context=day_id))

        for parsed in _time_ranges(day):
            if parsed.is_invalid:
                issues.append(ItineraryValidationIssue(BLOCKING, "invalid_activity_time_range", "Rendered activity contains an invalid or reversed time range.", context=day_id))
                continue
            if parsed.end_minutes is None:
                continue
            duration = parsed.end_minutes - int(parsed.start_minutes or 0)
            finishes_late = parsed.end_minutes >= 18 * 60
            if leisure and (duration >= 8 * 60 or finishes_late) and _FALSE_OPEN_TIME_RE.search(leisure) and not _CONSTRAINED_TIME_RE.search(leisure):
                issues.append(ItineraryValidationIssue(BLOCKING, "impossible_free_time_claim", "Free-time copy conflicts with a full-day or late-finishing activity.", context=f"{day_id}: {leisure}"))

        return_match = _RETURN_RE.search(f"{getattr(day, 'title', '')}. {intro}")
        if return_match and city and city.casefold() not in seen_cities:
            issues.append(ItineraryValidationIssue(BLOCKING, "false_return_visit", "Return-visit wording is used before the destination has appeared in an earlier chapter.", context=f"{day_id}: {city}"))
        if city:
            seen_cities.add(city.casefold())
        issues.extend(_title_consistency_issues(day))

    summary = getattr(document, "summary", None)
    for row in getattr(summary, "journey_arc", []) or []:
        experience = _text(row.get("experience", "") if isinstance(row, Mapping) else getattr(row, "experience", ""))
        experience_l = experience.casefold()
        for label, evidence in _SUPPORTED_ENTITY_MARKERS:
            if label in experience_l and not any(marker in full_body.casefold() for marker in evidence):
                issues.append(ItineraryValidationIssue(BLOCKING, "unsupported_journey_overview_fact", "Journey overview contains a fact not supported by any rendered day.", context=experience))
                break
    return issues


__all__ = ["client_truth_issues"]

"""Cross-layer truth checks for the final client render document.

These checks do not generate copy.  They verify that separately rendered title,
intro, activity, leisure, schedule, and journey-overview decisions still agree.
They consume the same time/occupancy contracts used by copy generation rather
than maintaining a second set of timing heuristics.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

from itinerary_generation.generation_quality_gate import BLOCKING, ItineraryValidationIssue
from itinerary_generation.itinerary_continuity import build_itinerary_continuity_report
from itinerary_generation.schedule_occupancy import analyze_time_intervals
from itinerary_generation.schedule_time_ranges import ParsedTimeRange, parse_time_range
from shared.text import clean_space

_INTERNAL_COPY_RE = re.compile(
    r"\b(?:raw supplier notes?|internal fallback|developer(?:-| )only|implementation detail|debug output|generated placeholder)\b",
    re.IGNORECASE,
)
_FALSE_OPEN_TIME_RE = re.compile(
    r"\b(?:rest of the day|schedule stays light|day remains light|time .* open|easy and flexible|remaining time .* flexible)\b",
    re.IGNORECASE,
)
_CONSTRAINED_TIME_RE = re.compile(
    r"\b(?:no additional plans|practical around dinner and rest|occupies most of the day|until the confirmed activity timing)\b",
    re.IGNORECASE,
)
_RETURN_RE = re.compile(r"\b(?:return to|back in)\s+(.+?)(?:[.,]|$)", re.IGNORECASE)
_DEPARTURE_FROM_RE = re.compile(
    r"\bdeparture from\s+([a-zA-ZÀ-ÖØ-öø-ÿ .']+?)(?:\s*[-–—?]|[.,|]|$)",
    re.IGNORECASE,
)
_MALFORMED_TITLE_RE = re.compile(r"(?:^|\s)(?:-\s*)?\?\s*$|\b(?:tba|unknown destination)\b", re.IGNORECASE)
_WORD_RE = re.compile(r"[a-zA-ZÀ-ÖØ-öø-ÿ]{3,}")
_NAMED_PHRASE_RE = re.compile(
    r"\b(?:[A-ZÀ-ÖØ-Þ][a-zA-ZÀ-ÖØ-öø-ÿ'’-]+(?:\s+|$)){2,}",
)
_STOP_WORDS = {
    "with", "from", "your", "today", "tour", "private", "guided", "experience",
    "full", "half", "ticket", "admission", "transfer", "return", "best", "highlights",
    "welcome", "arrival", "departure", "journey", "travel", "stay", "time", "days",
    "discovery", "arranged", "local", "scenic", "route", "city", "and", "the",
}
_SUPPORTED_ENTITY_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("vasa", ("vasa",)),
    ("tivoli gardens", ("tivoli", "tivoli gardens")),
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
    return clean_space(value)


def _normalised_place(value: object) -> str:
    text = _text(value).casefold()
    text = re.sub(r"\b(?:airport|railway station|train station|harbour|harbor|terminal)\b", "", text)
    return re.sub(r"[^a-zà-öø-ÿ]+", " ", text).strip()


def _day_body(day: Any) -> str:
    parts = [
        _text(getattr(day, "city", "")),
        _text(getattr(day, "title", "")),
        _text(getattr(day, "intro", "")),
    ]
    for block in getattr(day, "blocks", []) or []:
        parts.extend((_text(getattr(block, "section_title", "")), _text(getattr(block, "title", "")), _text(getattr(block, "description", ""))))
        parts.extend(_text(item) for item in getattr(block, "includes", []) or [])
        parts.extend(_text(item) for item in getattr(block, "lines", []) or [])
        for section in getattr(block, "extra_sections", []) or []:
            parts.append(_text(getattr(section, "title", "")))
            parts.extend(_text(item) for item in getattr(section, "items", []) or [])
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


def _time_ranges(day: Any) -> list[ParsedTimeRange]:
    parsed_ranges: list[ParsedTimeRange] = []
    for block in _activity_blocks(day):
        for meta in getattr(block, "meta", []) or []:
            if "time" not in _text(getattr(meta, "label", "")).casefold():
                continue
            parsed = parse_time_range(getattr(meta, "value", ""))
            if parsed.start_minutes is not None or parsed.is_invalid:
                parsed_ranges.append(parsed)
    return parsed_ranges


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
    location_tokens = _meaningful_tokens(_text(getattr(day, "city", "")))
    day_tokens = _meaningful_tokens(day_title) - location_tokens
    activity_tokens = _meaningful_tokens(activity_title) - location_tokens
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


def _block_signature(block: Any) -> tuple[str, ...]:
    return tuple(
        _text(value).casefold()
        for value in (
            getattr(block, "kind", ""),
            getattr(block, "section_title", ""),
            getattr(block, "title", ""),
            getattr(block, "description", ""),
            " | ".join(getattr(block, "lines", []) or []),
            " | ".join(getattr(block, "includes", []) or []),
        )
    )


def _duplicate_block_issues(day: Any) -> Iterable[ItineraryValidationIssue]:
    seen: dict[tuple[str, ...], int] = {}
    for index, block in enumerate(getattr(day, "blocks", []) or []):
        signature = _block_signature(block)
        if not any(signature[1:]):
            continue
        if signature in seen:
            yield ItineraryValidationIssue(
                BLOCKING,
                "duplicate_rendered_block",
                "The same client-facing block is rendered more than once on one day.",
                context=f"{getattr(day, 'day', '')}: blocks {seen[signature] + 1} and {index + 1}",
            )
            return
        seen[signature] = index


def _day_structure_issues(day: Any) -> Iterable[ItineraryValidationIssue]:
    day_id = _text(getattr(day, "day", ""))
    city = _text(getattr(day, "city", ""))
    title = _text(getattr(day, "title", ""))
    if title and _MALFORMED_TITLE_RE.search(title):
        yield ItineraryValidationIssue(
            BLOCKING,
            "malformed_client_title",
            "Day title contains an unresolved placeholder or dangling question mark.",
            context=f"{day_id}: {title}",
        )

    departure = _DEPARTURE_FROM_RE.search(title)
    if departure and city:
        departure_place = _normalised_place(departure.group(1))
        city_place = _normalised_place(city)
        if departure_place and city_place and departure_place not in city_place and city_place not in departure_place:
            yield ItineraryValidationIssue(
                BLOCKING,
                "day_destination_title_disagreement",
                "Departure title conflicts with the rendered day destination.",
                context=f"{day_id}: {title} <> {city}",
            )


def _named_phrase_is_supported(experience: str, chapter: str, full_body: str) -> bool:
    body_tokens = _meaningful_tokens(full_body)
    chapter_tokens = _meaningful_tokens(chapter)
    for match in _NAMED_PHRASE_RE.finditer(experience):
        phrase = _text(match.group(0))
        phrase_tokens = _meaningful_tokens(phrase) - chapter_tokens
        if len(phrase_tokens) >= 2 and not phrase_tokens.intersection(body_tokens):
            return False
    return True


def _overview_issues(summary: Any, full_body: str) -> Iterable[ItineraryValidationIssue]:
    full_body_l = full_body.casefold()
    for row in getattr(summary, "journey_arc", []) or []:
        experience = _text(row.get("experience", "") if isinstance(row, Mapping) else getattr(row, "experience", ""))
        chapter = _text(row.get("chapter", "") if isinstance(row, Mapping) else getattr(row, "chapter", ""))
        experience_l = experience.casefold()
        unsupported = False
        for label, evidence in _SUPPORTED_ENTITY_MARKERS:
            if label in experience_l and not any(marker in full_body_l for marker in evidence):
                unsupported = True
                break
        if not unsupported and not _named_phrase_is_supported(experience, chapter, full_body):
            unsupported = True
        if unsupported:
            yield ItineraryValidationIssue(
                BLOCKING,
                "unsupported_journey_overview_fact",
                "Journey overview contains a fact not supported by any rendered day.",
                context=experience,
            )


def _source_rows_text(source_rows: Iterable[Mapping[str, object]] | None) -> str:
    return " ".join(
        _text(value)
        for row in source_rows or ()
        for value in (
            row.get("city", ""),
            row.get("title", ""),
            row.get("original_title", ""),
            row.get("details", ""),
            " ".join(_text(item) for item in row.get("includes", []) or ()),
            " ".join(_text(item) for item in row.get("notable_sights", []) or ()),
        )
        if _text(value)
    )


def client_truth_issues(
    document: Any,
    *,
    source_rows: Iterable[Mapping[str, object]] | None = None,
) -> list[ItineraryValidationIssue]:
    issues: list[ItineraryValidationIssue] = []
    days = list(getattr(document, "days", []) or [])
    full_body = " ".join(
        part for part in (" ".join(_day_body(day) for day in days), _source_rows_text(source_rows)) if part
    )

    if _INTERNAL_COPY_RE.search(full_body):
        issues.append(ItineraryValidationIssue(BLOCKING, "internal_copy_leak", "Internal/developer wording leaked into client-facing output."))

    continuity_report = getattr(document, "continuity_report", None)
    if continuity_report is None and source_rows is not None:
        continuity_report = build_itinerary_continuity_report(source_rows)
    for finding in getattr(continuity_report, "findings", ()) or ():
        issues.append(
            ItineraryValidationIssue(
                finding.severity,
                finding.code,
                finding.message,
                context=finding.context,
            )
        )

    for day in days:
        day_id = _text(getattr(day, "day", ""))
        city = _text(getattr(day, "city", ""))
        intro = _text(getattr(day, "intro", ""))
        leisure = _leisure_text(day)
        if intro and leisure and intro.casefold() == leisure.casefold():
            issues.append(ItineraryValidationIssue(BLOCKING, "duplicate_intro_and_leisure", "Day intro and free-time copy are identical.", context=day_id))

        parsed_ranges = _time_ranges(day)
        if any(parsed.is_invalid for parsed in parsed_ranges):
            issues.append(ItineraryValidationIssue(BLOCKING, "invalid_activity_time_range", "Rendered activity contains an invalid or reversed time range.", context=day_id))
        intervals = [
            (int(parsed.start_minutes), int(parsed.end_minutes))
            for parsed in parsed_ranges
            if parsed.start_minutes is not None and parsed.end_minutes is not None and not parsed.is_invalid
        ]
        occupancy = analyze_time_intervals(intervals, has_invalid_time_range=any(parsed.is_invalid for parsed in parsed_ranges))
        if leisure and (occupancy.is_full_day or occupancy.finishes_late) and _FALSE_OPEN_TIME_RE.search(leisure) and not _CONSTRAINED_TIME_RE.search(leisure):
            issues.append(ItineraryValidationIssue(BLOCKING, "impossible_free_time_claim", "Free-time copy conflicts with the combined full-day or late-finishing activity schedule.", context=f"{day_id}: {leisure}"))

        return_match = _RETURN_RE.search(f"{getattr(day, 'title', '')}. {intro}")
        continuity_state = continuity_report.day_state(day_id) if continuity_report is not None else None
        if return_match and continuity_state is not None and not continuity_state.return_visit:
            issues.append(ItineraryValidationIssue(BLOCKING, "false_return_visit", "Return-visit wording conflicts with the canonical itinerary continuity state.", context=f"{day_id}: {city}"))

        issues.extend(_title_consistency_issues(day))
        issues.extend(_duplicate_block_issues(day))
        issues.extend(_day_structure_issues(day))

    summary = getattr(document, "summary", None)
    if summary is not None:
        issues.extend(_overview_issues(summary, full_body))
    return issues


__all__ = ["client_truth_issues"]

"""Authoritative itinerary schedule and geographic-continuity validation.

This module owns factual continuity checks that must be shared by the early
parsed-row gate, the structured document, and the late client-output gate.
It never writes or repairs itinerary copy.  It reports conflicts and leaves
source rows unchanged.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from itinerary_generation.day_grouping_utils import get_day_number
from itinerary_generation.day_timeline_events import TimelineEvent, canonical_event_city, normalize_day_events
from itinerary_generation.row_filters import get_commercial_status, get_row_type, is_optional_row
from itinerary_generation.schedule_time_ranges import ParsedTimeRange, parse_time_range
from shared.source_rows import row_ids_for_rows
from shared.text import clean_space

ERROR = "error"
WARNING = "warning"


@dataclass(frozen=True)
class ContinuityFinding:
    """One immutable continuity problem linked to its source rows."""

    severity: str
    code: str
    message: str
    context: str = ""
    source_row_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class _ScheduledActivity:
    day: str
    row_id: str
    title: str
    time_text: str
    parsed: ParsedTimeRange


@dataclass(frozen=True)
class _DayContinuityFacts:
    day: str
    rows: tuple[Mapping[str, Any], ...]
    row_ids: tuple[str, ...]
    events: tuple[TimelineEvent, ...]
    route_events: tuple[TimelineEvent, ...]
    accommodation_places: tuple[str, ...]
    arrival_places: tuple[str, ...]
    leisure_places: tuple[str, ...]
    departure_places: tuple[str, ...]
    fallback_place: str = ""


def _clean(value: object) -> str:
    return clean_space(value)


def _included_rows(rows: Iterable[Mapping[str, Any]] | None) -> list[Mapping[str, Any]]:
    result: list[Mapping[str, Any]] = []
    for row in rows or ():
        if not isinstance(row, Mapping):
            continue
        if is_optional_row(dict(row)) or get_commercial_status(dict(row)) == "excluded":
            continue
        result.append(row)
    return result


def _group_rows(rows: Sequence[Mapping[str, Any]]) -> OrderedDict[str, list[Mapping[str, Any]]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    first_seen: dict[str, int] = {}
    for index, row in enumerate(rows):
        day = _clean(row.get("day")) or "Day 0"
        grouped.setdefault(day, []).append(row)
        first_seen.setdefault(day, index)
    ordered = sorted(grouped, key=lambda day: (get_day_number(day), first_seen[day]))
    return OrderedDict((day, grouped[day]) for day in ordered)


def _canonical_place(value: object) -> str:
    return canonical_event_city(value)


def _place_key(value: object) -> str:
    place = _canonical_place(value) or _clean(value)
    return " ".join(place.casefold().replace("’", "'").split())


def _same_place(left: object, right: object) -> bool:
    left_key, right_key = _place_key(left), _place_key(right)
    if not left_key or not right_key:
        return False
    return left_key == right_key


def _row_title(row: Mapping[str, Any]) -> str:
    return _clean(row.get("title") or row.get("original_title") or row.get("details") or get_row_type(dict(row)) or "Arrangement")


def _activity_time(row: Mapping[str, Any]) -> tuple[str, ParsedTimeRange]:
    value = _clean(row.get("time"))
    if not value:
        details = _clean(row.get("details"))
        value = details if "time" in details.casefold() else ""
    if not value:
        return "", ParsedTimeRange()
    # Alternative supplier departures are choices, not simultaneous arranged
    # commitments.  Only one unambiguous range is eligible for overlap checks.
    lowered = value.casefold()
    if " / " in value or " or " in lowered:
        return value, ParsedTimeRange(reason="alternative_time_options")
    return value, parse_time_range(value)


def _scheduled_activities(day: str, rows: Sequence[Mapping[str, Any]]) -> list[_ScheduledActivity]:
    ids = row_ids_for_rows(rows)
    result: list[_ScheduledActivity] = []
    for row, row_id in zip(rows, ids):
        if get_row_type(dict(row)) != "Activity":
            continue
        time_text, parsed = _activity_time(row)
        if parsed.start_minutes is None or parsed.end_minutes is None or parsed.is_invalid:
            continue
        result.append(
            _ScheduledActivity(
                day=day,
                row_id=row_id,
                title=_row_title(row),
                time_text=time_text,
                parsed=parsed,
            )
        )
    return sorted(result, key=lambda item: (int(item.parsed.start_minutes or 0), int(item.parsed.end_minutes or 0), item.row_id))


def _overlap_findings(grouped: OrderedDict[str, list[Mapping[str, Any]]]) -> list[ContinuityFinding]:
    findings: list[ContinuityFinding] = []
    for day, rows in grouped.items():
        scheduled = _scheduled_activities(day, rows)
        for index, current in enumerate(scheduled):
            current_end = int(current.parsed.end_minutes or 0)
            for later in scheduled[index + 1 :]:
                later_start = int(later.parsed.start_minutes or 0)
                if later_start >= current_end:
                    break
                later_end = int(later.parsed.end_minutes or 0)
                if later_end <= int(current.parsed.start_minutes or 0):
                    continue
                findings.append(
                    ContinuityFinding(
                        severity=ERROR,
                        code="overlapping_arranged_activities",
                        message="Two included activities overlap in time and cannot both be completed as scheduled.",
                        context=f"{day}: {current.title} ({current.time_text}) overlaps {later.title} ({later.time_text})",
                        source_row_ids=(current.row_id, later.row_id),
                    )
                )
    return findings


def _unique_places(values: Iterable[object]) -> tuple[str, ...]:
    places: list[str] = []
    for value in values:
        place = _canonical_place(value)
        if place and not any(_same_place(place, current) for current in places):
            places.append(place)
    return tuple(places)


def _day_facts(day: str, rows: Sequence[Mapping[str, Any]]) -> _DayContinuityFacts:
    row_ids = row_ids_for_rows(rows)
    events = normalize_day_events(rows)
    route_events = tuple(event for event in events if event.is_route)
    accommodation_places = _unique_places(event.city for event in events if event.kind == "accommodation")
    arrival_places = _unique_places(event.city for event in events if event.kind == "arrival")
    leisure_places = _unique_places(event.city for event in events if event.kind in {"leisure", "onboard_leisure"})
    departure_places = _unique_places(event.city for event in events if event.kind == "departure")

    fallback_candidates: list[str] = []
    for event in events:
        if event.kind in {"arrival", "accommodation", "leisure"} and event.city:
            fallback_candidates.append(event.city)
    if not fallback_candidates:
        for event in events:
            if event.city:
                fallback_candidates.append(event.city)
    fallback_places = _unique_places(fallback_candidates)
    fallback_place = fallback_places[0] if fallback_places else ""

    return _DayContinuityFacts(
        day=day,
        rows=tuple(rows),
        row_ids=row_ids,
        events=events,
        route_events=route_events,
        accommodation_places=accommodation_places,
        arrival_places=arrival_places,
        leisure_places=leisure_places,
        departure_places=departure_places,
        fallback_place=fallback_place,
    )


def _event_row_ids(event: TimelineEvent) -> tuple[str, ...]:
    return (event.source_row_id,) if event.source_row_id else ()


def _route_label(event: TimelineEvent) -> str:
    origin = event.origin or "unspecified origin"
    destination = event.destination or "unspecified destination"
    return f"{origin} → {destination}"


def _route_continuity_findings(
    facts: _DayContinuityFacts,
    *,
    previous_place: str,
) -> tuple[list[ContinuityFinding], str]:
    findings: list[ContinuityFinding] = []
    cursor = previous_place

    for route in facts.route_events:
        declared_origin = route.city if route.city and cursor and _same_place(route.city, cursor) else route.origin
        if declared_origin and cursor and not _same_place(declared_origin, cursor):
            findings.append(
                ContinuityFinding(
                    severity=ERROR,
                    code="route_origin_discontinuity",
                    message="A travel leg starts somewhere other than the traveller's established location.",
                    context=f"{facts.day}: expected {cursor}, but route is {_route_label(route)}",
                    source_row_ids=_event_row_ids(route),
                )
            )
        if declared_origin and not cursor:
            cursor = declared_origin
        if route.destination:
            cursor = route.destination

    return findings, cursor


def _accommodation_findings(
    facts: _DayContinuityFacts,
    *,
    previous_place: str,
    route_end_place: str,
) -> tuple[list[ContinuityFinding], str]:
    findings: list[ContinuityFinding] = []
    hotels = facts.accommodation_places
    if not hotels:
        expected = route_end_place or previous_place
        presence_place = (facts.arrival_places or facts.leisure_places or facts.departure_places)
        if not presence_place:
            return findings, expected
        place = presence_place[-1]
        if expected and not _same_place(place, expected):
            if facts.route_events:
                findings.append(
                    ContinuityFinding(
                        severity=ERROR,
                        code="travel_destination_day_location_mismatch",
                        message="The arranged travel destination does not match the destination used by the rest of the day.",
                        context=f"{facts.day}: travel ends in {expected}, day location is {place}",
                        source_row_ids=facts.row_ids,
                    )
                )
            elif facts.arrival_places:
                findings.append(
                    ContinuityFinding(
                        severity=WARNING,
                        code="arrival_without_travel_leg",
                        message="The itinerary establishes arrival in a new destination without an explicit arranged or self-arranged travel leg.",
                        context=f"{facts.day}: {previous_place} → {place}",
                        source_row_ids=facts.row_ids,
                    )
                )
            else:
                findings.append(
                    ContinuityFinding(
                        severity=ERROR,
                        code="unexplained_destination_jump",
                        message="The itinerary changes destination without an arranged or self-arranged travel leg.",
                        context=f"{facts.day}: {previous_place} → {place}",
                        source_row_ids=facts.row_ids,
                    )
                )
        return findings, place

    hotel_place = hotels[-1]
    if len(hotels) > 1 and not facts.route_events:
        findings.append(
            ContinuityFinding(
                severity=ERROR,
                code="multiple_accommodation_cities_without_travel",
                message="The same day contains accommodation in different destinations without a travel leg connecting them.",
                context=f"{facts.day}: {' → '.join(hotels)}",
                source_row_ids=facts.row_ids,
            )
        )
        return findings, hotel_place

    expected = route_end_place or previous_place
    if expected and not _same_place(hotel_place, expected):
        if facts.route_events:
            findings.append(
                ContinuityFinding(
                    severity=ERROR,
                    code="travel_destination_accommodation_mismatch",
                    message="The arranged travel destination does not match the accommodation location that follows.",
                    context=f"{facts.day}: travel ends in {expected}, accommodation is in {hotel_place}",
                    source_row_ids=facts.row_ids,
                )
            )
        elif any(_same_place(hotel_place, place) for place in facts.arrival_places):
            findings.append(
                ContinuityFinding(
                    severity=WARNING,
                    code="arrival_without_travel_leg",
                    message="The itinerary establishes arrival in a new destination without an explicit arranged or self-arranged travel leg.",
                    context=f"{facts.day}: {previous_place} → {hotel_place}",
                    source_row_ids=facts.row_ids,
                )
            )
        else:
            findings.append(
                ContinuityFinding(
                    severity=ERROR,
                    code="unexplained_destination_jump",
                    message="The itinerary changes accommodation destination without an arranged or self-arranged travel leg.",
                    context=f"{facts.day}: {previous_place} → {hotel_place}",
                    source_row_ids=facts.row_ids,
                )
            )
    return findings, hotel_place


def _geographic_findings(grouped: OrderedDict[str, list[Mapping[str, Any]]]) -> list[ContinuityFinding]:
    findings: list[ContinuityFinding] = []
    established_place = ""

    for day, rows in grouped.items():
        facts = _day_facts(day, rows)
        route_findings, route_end = _route_continuity_findings(facts, previous_place=established_place)
        findings.extend(route_findings)

        accommodation_findings, day_end = _accommodation_findings(
            facts,
            previous_place=established_place,
            route_end_place=route_end,
        )
        findings.extend(accommodation_findings)

        if day_end:
            established_place = day_end
        elif not established_place:
            established_place = facts.fallback_place

    return findings


def evaluate_itinerary_continuity(rows: Iterable[Mapping[str, Any]] | None) -> tuple[ContinuityFinding, ...]:
    """Return deterministic schedule and route-continuity findings.

    Optional and excluded rows do not participate.  Self-arranged transport is
    retained because it is valid continuity evidence even when it is excluded
    from arranged pricing.
    """

    included = _included_rows(rows)
    grouped = _group_rows(included)
    findings = _overlap_findings(grouped)
    findings.extend(_geographic_findings(grouped))
    return tuple(findings)


__all__ = [
    "ERROR",
    "WARNING",
    "ContinuityFinding",
    "evaluate_itinerary_continuity",
]

"""Schedule and geographic findings for canonical itinerary continuity."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from datetime import date, datetime
from typing import Mapping, Sequence

from itinerary_generation.itinerary_continuity_facts import (
    _DayContinuityFacts,
    _canonical_place,
    _clean,
    _day_facts,
    _event_row_ids,
    _is_departure_side_place_before_overnight,
    _overnight_route_destination,
    _route_label,
    _row_title,
    _same_place,
)
from itinerary_generation.itinerary_continuity_models import ContinuityFinding, ERROR, WARNING
from itinerary_generation.row_filters import get_row_type
from itinerary_generation.schedule_time_ranges import ParsedTimeRange, parse_time_range
from shared.source_rows import row_ids_for_rows


@dataclass(frozen=True)
class _ScheduledActivity:
    day: str
    row_id: str
    title: str
    time_text: str
    parsed: ParsedTimeRange

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
                overnight_destination = _overnight_route_destination(facts)
                if not (
                    overnight_destination
                    and _is_departure_side_place_before_overnight(
                        facts,
                        place,
                        previous_place=previous_place,
                    )
                ):
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
        # Daytime content before an overnight route remains owned by the
        # departure chapter, while the overnight destination establishes the
        # traveller's location for the following morning.
        if facts.route_events and _overnight_route_destination(facts):
            return findings, route_end_place or expected
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

def _parse_date(value: object) -> date | None:
    text = _clean(value)
    if not text:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None

def _accommodation_overlap_findings(rows: Sequence[Mapping[str, Any]]) -> list[ContinuityFinding]:
    stays: list[tuple[date, date, str, str, str]] = []
    for index, row in enumerate(rows):
        if get_row_type(dict(row)) != "Hotel":
            continue
        start = _parse_date(row.get("start_date") or row.get("from_date"))
        end = _parse_date(row.get("end_date") or row.get("to_date"))
        if start is None or end is None or end <= start:
            continue
        stays.append((start, end, _canonical_place(row.get("city")), _row_title(row), row_ids_for_rows((row,))[0]))
    findings: list[ContinuityFinding] = []
    for index, first in enumerate(stays):
        for second in stays[index + 1 :]:
            if max(first[0], second[0]) >= min(first[1], second[1]):
                continue
            if _same_place(first[2], second[2]) and first[3].casefold() == second[3].casefold():
                continue
            findings.append(
                ContinuityFinding(
                    severity=ERROR,
                    code="overlapping_accommodation_stays",
                    message="Included accommodation stays overlap and cannot both be occupied as scheduled.",
                    context=f"{first[3]} ({first[0]}–{first[1]}) overlaps {second[3]} ({second[0]}–{second[1]})",
                    source_row_ids=(first[4], second[4]),
                )
            )
    return findings


__all__ = [
    "_accommodation_findings",
    "_accommodation_overlap_findings",
    "_geographic_findings",
    "_overlap_findings",
    "_route_continuity_findings",
]

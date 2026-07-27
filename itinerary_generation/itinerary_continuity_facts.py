"""Row grouping and timeline facts shared by continuity findings and day state."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from itinerary_generation.day_grouping_utils import get_day_number
from itinerary_generation.day_timeline_events import TimelineEvent, canonical_event_city, normalize_day_events
from itinerary_generation.row_filters import get_commercial_status, get_row_type, is_optional_row
from shared.source_rows import row_ids_for_rows
from shared.text import clean_space


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

def _overnight_route_destination(facts: _DayContinuityFacts) -> str:
    """Return the final destination established by overnight movement."""

    return next(
        (event.destination for event in reversed(facts.route_events) if event.is_overnight and event.destination),
        "",
    )

def _daytime_place_before_overnight(facts: _DayContinuityFacts) -> str:
    """Return the last local place visited before the first overnight route."""

    first_overnight_route = next((event for event in facts.route_events if event.is_overnight), None)
    if first_overnight_route is None:
        return ""
    return next(
        (
            _canonical_place(event.city)
            for event in reversed(facts.events)
            if event.order < first_overnight_route.order
            and event.kind in {"activity", "leisure", "arrival", "accommodation"}
            and event.city
        ),
        "",
    )

def _is_departure_side_place_before_overnight(
    facts: _DayContinuityFacts,
    place: str,
    *,
    previous_place: str,
) -> bool:
    """Return whether ``place`` belongs to the route before the overnight leg."""

    first_overnight = next((event for event in facts.route_events if event.is_overnight), None)
    if first_overnight is None:
        return False
    candidates: list[str] = [previous_place]
    for event in facts.route_events:
        if event.order > first_overnight.order:
            break
        candidates.extend((event.origin, event.city))
        if event.order < first_overnight.order:
            candidates.append(event.destination)
    return any(_same_place(place, candidate) for candidate in candidates if candidate)


__all__ = [
    "_DayContinuityFacts",
    "_canonical_place",
    "_clean",
    "_day_facts",
    "_daytime_place_before_overnight",
    "_event_row_ids",
    "_group_rows",
    "_included_rows",
    "_is_departure_side_place_before_overnight",
    "_overnight_route_destination",
    "_place_key",
    "_route_label",
    "_row_title",
    "_same_place",
    "_unique_places",
]

"""Destination visit-memory helpers for repeated-city copy."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

from itinerary_generation.common import get_primary_city
from itinerary_generation.destination_registry import destination_for_alias
from itinerary_generation.day_timeline_events import canonical_event_city, normalize_day_events
from text_polish import polish_title


@dataclass(frozen=True)
class DayDestinationMemory:
    """Fact-only memory of how a destination has appeared so far."""

    day: str = ""
    primary_city: str = ""
    canonical_city: str = ""
    visit_number: int = 1
    previous_days: tuple[str, ...] = ()
    overnight_city: str = ""
    previous_overnight_city: str = ""
    transit_cities: tuple[str, ...] = ()
    first_visit: bool = True
    return_visit: bool = False
    transit_only: bool = False
    completed_visit: bool = False
    chapter_start: bool = False
    flags: frozenset[str] = field(default_factory=frozenset)


def canonical_memory_city(value: object) -> str:
    text = polish_title(str(value or "").strip())
    if not text:
        return ""
    record = destination_for_alias(text)
    return record.name if record else text


def _day_sort_key(day: object, index: int) -> tuple[int, int, str]:
    text = str(day or "")
    digits = "".join(ch for ch in text if ch.isdigit())
    return (int(digits) if digits else index + 1_000_000, index, text)


def build_destination_visit_memory(grouped_days: Mapping[str, Sequence[dict]] | Iterable[tuple[str, Sequence[dict]]]) -> dict[str, DayDestinationMemory]:
    """Return visit memory keyed by day label.

    A route endpoint is not a completed visit.  A destination becomes visited
    only through a stay, a local activity/leisure chapter, or an arrival that
    does not immediately continue elsewhere.  Consecutive days in the same
    chapter keep the same visit number; explicit re-arrivals start a new one.
    """

    items = list(grouped_days.items()) if isinstance(grouped_days, Mapping) else list(grouped_days)
    indexed_items = list(enumerate(items))
    indexed_items.sort(key=lambda item: _day_sort_key(item[1][0], item[0]))

    visit_starts: dict[str, list[str]] = defaultdict(list)
    active_city = ""
    active_overnight_city = ""
    active_visit_number = 1
    memories: dict[str, DayDestinationMemory] = {}

    for _, (day, rows) in indexed_items:
        day_label = str(day or "")
        events = normalize_day_events(rows or [])
        hotel_cities = [event.city for event in events if event.kind == "accommodation" and event.city]
        route_destinations = [event.destination for event in events if event.destination]
        local_experience_cities = [
            event.city for event in events
            if event.kind in {"activity", "leisure", "onboard_leisure"} and event.city
        ]
        has_arrival = any(event.kind == "arrival" for event in events)
        route_origins = [event.origin for event in events if event.kind == "route_transport" and event.origin]
        has_onward_route = any(event.kind == "route_transport" and event.destination for event in events)
        primary = polish_title(get_primary_city(rows or []) or "")
        overnight_city = hotel_cities[-1] if hotel_cities else ""

        completed_city = overnight_city
        if not completed_city and local_experience_cities:
            completed_city = local_experience_cities[-1]
        if not completed_city and has_arrival and not has_onward_route:
            completed_city = primary

        context_city = completed_city or (route_destinations[-1] if route_destinations else "") or primary
        canonical = canonical_memory_city(context_city)
        completed_visit = bool(completed_city and canonical)

        transit_cities: list[str] = []
        for event in events:
            for city in (event.origin, event.city):
                candidate = canonical_event_city(city)
                if candidate and canonical and canonical_memory_city(candidate) != canonical and candidate not in transit_cities:
                    transit_cities.append(candidate)

        arrives_from_elsewhere = bool(
            completed_visit
            and canonical
            and any(canonical_memory_city(origin) not in {"", canonical} for origin in route_origins)
        )
        same_active_city = bool(active_city and canonical == active_city)
        explicit_new_chapter = bool(
            completed_visit
            and (
                arrives_from_elsewhere
                or (has_arrival and not same_active_city)
            )
        )
        chapter_start = bool(
            completed_visit
            and (
                not active_city
                or canonical != active_city
                or explicit_new_chapter
            )
        )
        if chapter_start:
            previous = tuple(visit_starts[canonical])
            active_visit_number = len(previous) + 1
            active_city = canonical
            visit_starts[canonical].append(day_label)
        elif completed_visit and canonical == active_city:
            previous = tuple(visit_starts[canonical][:-1])
        else:
            previous = tuple(visit_starts[canonical]) if canonical else ()

        previous_overnight_city = (
            active_overnight_city
            if active_overnight_city and canonical_memory_city(active_overnight_city) == canonical
            else ""
        )
        visit_number = active_visit_number if canonical and canonical == active_city else (len(previous) + 1 if canonical else 1)
        return_visit = bool(completed_visit and chapter_start and previous)
        transit_only = bool(context_city and not completed_visit)
        flags: set[str] = set()
        if return_visit:
            flags.add("return_visit")
        if completed_visit:
            flags.add("completed_visit")
        if chapter_start:
            flags.add("chapter_start")
        if transit_only:
            flags.add("transit_only")

        # Leaving the active city on a route-only day closes that visit
        # chapter.  A later hotel/activity in the same city is then a genuine
        # return rather than a continuation.
        leaves_active_city = bool(
            active_city
            and not completed_visit
            and any(
                canonical_memory_city(event.origin) == active_city
                and canonical_memory_city(event.destination) not in {"", active_city}
                for event in events
                if event.kind == "route_transport"
            )
        )

        memories[day_label] = DayDestinationMemory(
            day=day_label,
            primary_city=primary,
            canonical_city=canonical,
            visit_number=visit_number,
            previous_days=previous,
            overnight_city=overnight_city,
            previous_overnight_city=previous_overnight_city,
            transit_cities=tuple(transit_cities),
            first_visit=not return_visit,
            return_visit=return_visit,
            transit_only=transit_only,
            completed_visit=completed_visit,
            chapter_start=chapter_start,
            flags=frozenset(flags),
        )
        if overnight_city:
            active_overnight_city = overnight_city
        if leaves_active_city:
            active_city = ""
            active_overnight_city = ""
    return memories


__all__ = ["DayDestinationMemory", "build_destination_visit_memory", "canonical_memory_city"]

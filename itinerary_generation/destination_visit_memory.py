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
    transit_cities: tuple[str, ...] = ()
    first_visit: bool = True
    return_visit: bool = False
    transit_only: bool = False
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
    """Return visit memory keyed by day label."""

    items = list(grouped_days.items()) if isinstance(grouped_days, Mapping) else list(grouped_days)
    indexed_items = list(enumerate(items))
    indexed_items.sort(key=lambda item: _day_sort_key(item[1][0], item[0]))

    seen: dict[str, list[str]] = defaultdict(list)
    memories: dict[str, DayDestinationMemory] = {}
    for _, (day, rows) in indexed_items:
        day_label = str(day or "")
        events = normalize_day_events(rows or [])
        hotel_cities = [event.city for event in events if event.kind == "accommodation" and event.city]
        route_destinations = [event.destination for event in events if event.destination]
        primary = polish_title(get_primary_city(rows or []) or "")
        overnight_city = hotel_cities[-1] if hotel_cities else ""
        memory_city = overnight_city or (route_destinations[-1] if route_destinations else "") or primary
        canonical = canonical_memory_city(memory_city)
        transit_cities: list[str] = []
        for event in events:
            for city in (event.origin, event.city):
                candidate = canonical_event_city(city)
                if candidate and canonical and canonical_memory_city(candidate) != canonical and candidate not in transit_cities:
                    transit_cities.append(candidate)
        previous = tuple(seen[canonical]) if canonical else ()
        visit_number = len(previous) + 1 if canonical else 1
        flags: set[str] = set()
        if visit_number > 1:
            flags.add("return_visit")
        if transit_cities and not overnight_city and primary and canonical_memory_city(primary) not in {canonical, ""}:
            flags.add("transit_city_present")
        memories[day_label] = DayDestinationMemory(
            day=day_label,
            primary_city=primary,
            canonical_city=canonical,
            visit_number=visit_number,
            previous_days=previous,
            overnight_city=overnight_city,
            transit_cities=tuple(transit_cities),
            first_visit=visit_number <= 1,
            return_visit=visit_number > 1 and bool(canonical),
            transit_only=bool(primary and not overnight_city and transit_cities and canonical_memory_city(primary) != canonical),
            flags=frozenset(flags),
        )
        if canonical:
            seen[canonical].append(day_label)
    return memories


__all__ = ["DayDestinationMemory", "build_destination_visit_memory", "canonical_memory_city"]

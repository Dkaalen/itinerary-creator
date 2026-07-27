"""Destination visit-memory projection from canonical itinerary continuity."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

from itinerary_generation.destination_registry import destination_for_alias
from itinerary_generation.itinerary_continuity import (
    ItineraryContinuityReport,
    build_itinerary_continuity_report,
)
from text_polish import polish_title


@dataclass(frozen=True)
class DayDestinationMemory:
    """Fact-only memory projected from one canonical continuity day state."""

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
    day_trip_return: bool = False
    destination_arrival: bool = False
    arrival_stay: bool = False
    welcome_allowed: bool = False
    same_city_accommodation_change: bool = False
    stay_continuation: bool = False
    flags: frozenset[str] = field(default_factory=frozenset)


def canonical_memory_city(value: object) -> str:
    text = polish_title(str(value or "").strip())
    if not text:
        return ""
    record = destination_for_alias(text)
    return record.name if record else text


def _grouped_items(
    grouped_days: Mapping[str, Sequence[dict]] | Iterable[tuple[str, Sequence[dict]]],
) -> list[tuple[str, Sequence[dict]]]:
    return list(grouped_days.items()) if isinstance(grouped_days, Mapping) else list(grouped_days)


def build_destination_visit_memory(
    grouped_days: Mapping[str, Sequence[dict]] | Iterable[tuple[str, Sequence[dict]]],
    *,
    continuity_report: ItineraryContinuityReport | None = None,
) -> dict[str, DayDestinationMemory]:
    """Return visit memory keyed by day, projected from continuity once."""

    items = _grouped_items(grouped_days)
    report = continuity_report or build_itinerary_continuity_report(
        [row for _day, rows in items for row in rows]
    )
    result: dict[str, DayDestinationMemory] = {}
    for state in report.days:
        flags: set[str] = set()
        if state.return_visit:
            flags.add("return_visit")
        if state.completed_visit:
            flags.add("completed_visit")
        if state.chapter_start:
            flags.add("chapter_start")
        if state.transit_only:
            flags.add("transit_only")
        if state.day_trip_return:
            flags.add("day_trip_return")
        result[state.day] = DayDestinationMemory(
            day=state.day,
            primary_city=state.chapter_city or state.end_place,
            canonical_city=canonical_memory_city(state.chapter_city),
            visit_number=state.visit_number,
            previous_days=state.previous_visit_days,
            overnight_city=state.overnight_place,
            previous_overnight_city=state.previous_overnight_place,
            transit_cities=state.transit_cities,
            first_visit=not state.return_visit,
            return_visit=state.return_visit,
            transit_only=state.transit_only,
            completed_visit=state.completed_visit,
            chapter_start=state.chapter_start,
            day_trip_return=state.day_trip_return,
            destination_arrival=state.destination_arrival,
            arrival_stay=state.arrival_stay,
            welcome_allowed=state.welcome_allowed,
            same_city_accommodation_change=state.same_city_accommodation_change,
            stay_continuation=state.stay_continuation,
            flags=frozenset(flags),
        )
    return result


__all__ = ["DayDestinationMemory", "build_destination_visit_memory", "canonical_memory_city"]

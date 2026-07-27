"""Itinerary-level visit context for deterministic day copy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from itinerary_generation.destination_visit_memory import build_destination_visit_memory, canonical_memory_city
from itinerary_generation.itinerary_continuity import ItineraryContinuityReport


@dataclass(frozen=True)
class DayVisitContext:
    """Visit information for one itinerary day.

    The copy engine uses this to avoid treating a repeated city as a first
    arrival.  It is deliberately small and fact-only so it can be passed through
    render/preview/PDF code without becoming another rendering model.
    """

    day: str = ""
    city: str = ""
    canonical_city: str = ""
    visit_number: int = 1
    previous_days: tuple[str, ...] = ()
    overnight_city: str = ""
    previous_overnight_city: str = ""
    transit_cities: tuple[str, ...] = ()
    transit_only: bool = False
    completed_visit: bool = False
    chapter_start: bool = False
    return_visit: bool = False
    continuity_decisions_available: bool = False
    day_trip_return: bool = False
    destination_arrival: bool = False
    arrival_stay: bool = False
    welcome_allowed: bool = False
    same_city_accommodation_change: bool = False
    stay_continuation: bool = False

    @property
    def is_return_visit(self) -> bool:
        # Preserve compatibility for explicitly constructed contexts while
        # generated contexts use the stricter chapter-aware return flag.
        return self.return_visit or (
            self.visit_number > 1
            and bool(self.canonical_city)
            and not self.transit_only
        )


def _canonical_city(value: object) -> str:
    return canonical_memory_city(value)


def _day_sort_key(day: object, index: int) -> tuple[int, int, str]:
    text = str(day or "")
    digits = "".join(ch for ch in text if ch.isdigit())
    return (int(digits) if digits else index + 1_000_000, index, text)


def build_day_visit_contexts(
    grouped_days: Mapping[str, Sequence[dict]] | Iterable[tuple[str, Sequence[dict]]],
    *,
    continuity_report: ItineraryContinuityReport | None = None,
) -> dict[str, DayVisitContext]:
    """Return visit context keyed by day label for a grouped itinerary."""

    memories = build_destination_visit_memory(grouped_days, continuity_report=continuity_report)
    contexts: dict[str, DayVisitContext] = {}
    for day_label, memory in memories.items():
        contexts[day_label] = DayVisitContext(
            day=day_label,
            city=memory.primary_city or memory.overnight_city or memory.canonical_city,
            canonical_city=memory.canonical_city,
            visit_number=memory.visit_number,
            previous_days=memory.previous_days,
            overnight_city=memory.overnight_city,
            previous_overnight_city=memory.previous_overnight_city,
            transit_cities=memory.transit_cities,
            transit_only=memory.transit_only,
            completed_visit=memory.completed_visit,
            chapter_start=memory.chapter_start,
            return_visit=memory.return_visit,
            continuity_decisions_available=True,
            day_trip_return=memory.day_trip_return,
            destination_arrival=memory.destination_arrival,
            arrival_stay=memory.arrival_stay,
            welcome_allowed=memory.welcome_allowed,
            same_city_accommodation_change=memory.same_city_accommodation_change,
            stay_continuation=memory.stay_continuation,
        )
    return contexts

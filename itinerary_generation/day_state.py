"""Itinerary-aware destination and arrival state for one day.

This module owns the distinction between a genuine destination arrival, a
continuation of an existing stay, a same-city accommodation change, and a
return visit.  Copy writers consume this state; they must not infer arrival
intent again from the mere presence of a Hotel row.
"""

from __future__ import annotations

from dataclasses import dataclass

from itinerary_generation.destination_visit_memory import canonical_memory_city


@dataclass(frozen=True)
class DayState:
    """Fact-only itinerary state used by title and intro decisions."""

    context_available: bool = False
    chapter_start: bool = False
    chapter_continuation: bool = False
    completed_visit: bool = False
    transit_only: bool = False
    return_visit: bool = False
    explicit_arrival: bool = False
    airport_arrival: bool = False
    arrival_onward: bool = False
    destination_arrival: bool = False
    arrival_stay: bool = False
    welcome_allowed: bool = False
    same_city_accommodation_change: bool = False
    stay_continuation: bool = False
    previous_overnight_city: str = ""


def _same_city(left: object, right: object) -> bool:
    left_city = canonical_memory_city(left)
    right_city = canonical_memory_city(right)
    return bool(left_city and right_city and left_city.casefold() == right_city.casefold())


def build_day_state(
    *,
    visit_context: object | None,
    has_arrival: bool,
    has_departure: bool,
    has_accommodation: bool,
    has_route_transport: bool,
    arrival_city: str,
    onward_destination: str,
    overnight_city: str,
    source_flags: set[str] | frozenset[str],
    same_city_change_signal: bool,
) -> DayState:
    """Return the sole itinerary-aware arrival/stay state for a day."""

    context_available = visit_context is not None
    canonical_decisions = bool(getattr(visit_context, "continuity_decisions_available", False)) if context_available else False
    chapter_start = bool(getattr(visit_context, "chapter_start", False)) if context_available else False
    completed_visit = bool(getattr(visit_context, "completed_visit", False)) if context_available else False
    transit_only = bool(getattr(visit_context, "transit_only", False)) if context_available else False
    return_visit = bool(getattr(visit_context, "is_return_visit", False)) if context_available else False
    previous_overnight_city = str(getattr(visit_context, "previous_overnight_city", "") or "")
    chapter_continuation = bool(
        context_available
        and completed_visit
        and not chapter_start
        and not return_visit
        and not transit_only
    )

    airport_arrival = "arrival_airport_transfer" in source_flags
    explicit_arrival = bool(has_arrival or airport_arrival)
    arrival_onward = bool(
        explicit_arrival
        and arrival_city
        and onward_destination
        and not _same_city(arrival_city, onward_destination)
    )

    inferred_hotel_arrival = bool(
        has_accommodation
        and not has_route_transport
        and (
            chapter_start
            if context_available
            else not same_city_change_signal
        )
    )
    route_arrival = bool(
        has_route_transport
        and has_accommodation
        and (chapter_start if context_available else True)
    )
    inferred_destination_arrival = bool(
        not return_visit
        and not arrival_onward
        and not chapter_continuation
        and (
            (explicit_arrival and (chapter_start if context_available else True))
            or inferred_hotel_arrival
            or route_arrival
        )
    )
    destination_arrival = (
        bool(getattr(visit_context, "destination_arrival", False))
        if canonical_decisions
        else inferred_destination_arrival
    )
    arrival_stay = (
        bool(getattr(visit_context, "arrival_stay", False))
        if canonical_decisions
        else bool(destination_arrival and not has_route_transport)
    )

    inferred_same_city_change = bool(
        same_city_change_signal
        or (
            context_available
            and chapter_continuation
            and has_accommodation
            and not has_route_transport
            and not has_departure
            and _same_city(previous_overnight_city, overnight_city)
        )
    )
    same_city_accommodation_change = (
        bool(getattr(visit_context, "same_city_accommodation_change", False))
        if canonical_decisions
        else inferred_same_city_change
    )
    stay_continuation = (
        bool(getattr(visit_context, "stay_continuation", False))
        if canonical_decisions
        else bool(chapter_continuation and not same_city_accommodation_change)
    )

    return DayState(
        context_available=context_available,
        chapter_start=chapter_start,
        chapter_continuation=chapter_continuation,
        completed_visit=completed_visit,
        transit_only=transit_only,
        return_visit=return_visit,
        explicit_arrival=explicit_arrival,
        airport_arrival=airport_arrival,
        arrival_onward=arrival_onward,
        destination_arrival=destination_arrival,
        arrival_stay=arrival_stay,
        welcome_allowed=(
            bool(getattr(visit_context, "welcome_allowed", False))
            if canonical_decisions
            else arrival_stay
        ),
        same_city_accommodation_change=same_city_accommodation_change,
        stay_continuation=stay_continuation,
        previous_overnight_city=previous_overnight_city,
    )


__all__ = ["DayState", "build_day_state"]

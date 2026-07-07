"""Accommodation-state facts for day-brain copy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from itinerary_generation.day_timeline_events import TimelineEvent


@dataclass(frozen=True)
class AccommodationState:
    """Fact-only accommodation state for a single day."""

    accommodation_cities: tuple[str, ...] = ()
    first_accommodation_city: str = ""
    tonight_city: str = ""
    has_accommodation: bool = False
    has_transfer_to_accommodation: bool = False
    has_transfer_between_stays: bool = False
    check_in_confirmed: bool = False
    check_out_confirmed: bool = False
    accommodation_change: bool = False
    same_city_change: bool = False
    new_city_change: bool = False
    mention_only: bool = False
    flags: frozenset[str] = field(default_factory=frozenset)


def _unique(items: Sequence[str]) -> tuple[str, ...]:
    result: list[str] = []
    for item in items:
        if item and item not in result:
            result.append(item)
    return tuple(result)


def build_accommodation_state(events: Sequence[TimelineEvent]) -> AccommodationState:
    """Return accommodation state from normalized events only."""

    accommodation_events = tuple(event for event in events or () if event.kind == "accommodation")
    accommodation_cities = _unique(tuple(event.city for event in accommodation_events))
    transfer_to_accommodation = tuple(
        event
        for event in events or ()
        if event.kind == "local_transfer" and event.target_kind == "accommodation"
    )
    transfer_between_stays = tuple(
        event
        for event in transfer_to_accommodation
        if any(marker in event.text.lower() for marker in ("between accommodations", "hotel to hotel", "next accommodation", "next stay", "your next accommodation"))
    )
    check_in_confirmed = bool(
        accommodation_events
        and (
            any("check_in" in event.flags for event in events or ())
            or any(event.kind == "arrival" for event in events or ())
            or any(event.kind == "accommodation" for event in events or ())
        )
    )
    check_out_confirmed = bool(
        any("check_out" in event.flags for event in events or ())
        or any(event.kind == "departure" for event in events or ())
        or any("hotel to airport" in event.text.lower() or "hotel to station" in event.text.lower() for event in events or ())
    )
    accommodation_change = bool(len(accommodation_events) >= 2 or transfer_between_stays)
    same_city_change = bool(accommodation_change and accommodation_cities and len(accommodation_cities) == 1)
    new_city_change = bool(accommodation_change and len(accommodation_cities) > 1)
    mention_only = bool(not accommodation_events and transfer_to_accommodation)
    flags: set[str] = set()
    if same_city_change:
        flags.add("same_city_accommodation_change")
    if new_city_change:
        flags.add("new_city_accommodation_change")
    if mention_only:
        flags.add("accommodation_transfer_without_stay")
    return AccommodationState(
        accommodation_cities=accommodation_cities,
        first_accommodation_city=accommodation_cities[0] if accommodation_cities else "",
        tonight_city=accommodation_cities[-1] if accommodation_cities else "",
        has_accommodation=bool(accommodation_events),
        has_transfer_to_accommodation=bool(transfer_to_accommodation),
        has_transfer_between_stays=bool(transfer_between_stays),
        check_in_confirmed=check_in_confirmed,
        check_out_confirmed=check_out_confirmed,
        accommodation_change=accommodation_change,
        same_city_change=same_city_change,
        new_city_change=new_city_change,
        mention_only=mention_only,
        flags=frozenset(flags),
    )


__all__ = ["AccommodationState", "build_accommodation_state"]

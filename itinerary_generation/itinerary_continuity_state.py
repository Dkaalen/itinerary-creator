"""Canonical per-day continuity-state projection."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Mapping

from itinerary_generation.itinerary_continuity_facts import (
    _DayContinuityFacts,
    _canonical_place,
    _day_facts,
    _daytime_place_before_overnight,
    _overnight_route_destination,
    _place_key,
    _same_place,
)
from itinerary_generation.itinerary_continuity_findings import (
    _accommodation_findings,
    _route_continuity_findings,
)
from itinerary_generation.itinerary_continuity_models import DayContinuityState


def _transit_cities(facts: _DayContinuityFacts, chapter_city: str) -> tuple[str, ...]:
    values: list[str] = []
    for event in facts.events:
        for value in (event.origin, event.city, event.destination):
            city = _canonical_place(value)
            if city and not _same_place(city, chapter_city) and not any(_same_place(city, current) for current in values):
                values.append(city)
    return tuple(values)

def _build_day_states(grouped: OrderedDict[str, list[Mapping[str, Any]]]) -> tuple[DayContinuityState, ...]:
    established_place = ""
    previous_overnight = ""
    active_accommodation_place = ""
    active_chapter = ""
    visits: dict[str, list[str]] = {}
    states: list[DayContinuityState] = []

    for day, rows in grouped.items():
        facts = _day_facts(day, rows)
        start_place = established_place
        _route_findings, route_end = _route_continuity_findings(facts, previous_place=start_place)
        _hotel_findings, day_end = _accommodation_findings(
            facts, previous_place=start_place, route_end_place=route_end
        )
        end_place = day_end or route_end or start_place or facts.fallback_place
        overnight_route_destination = _overnight_route_destination(facts)
        overnight_place = (
            facts.accommodation_places[-1]
            if facts.accommodation_places
            else overnight_route_destination or end_place
        )
        day_trip_return = bool(
            start_place
            and end_place
            and _same_place(start_place, end_place)
            and not overnight_route_destination
            and any(
                event.destination and not _same_place(event.destination, start_place)
                for event in facts.route_events
            )
        )
        has_local_content = any(
            event.kind in {"activity", "leisure", "onboard_leisure", "accommodation", "arrival"}
            for event in facts.events
        )
        daytime_place_before_overnight = _daytime_place_before_overnight(facts)
        # A daytime experience belongs to the place where it occurs even when
        # an overnight train/cruise establishes the following morning's base.
        # The overnight destination remains ``overnight_place`` and becomes the
        # next day's established location; it must not rewrite today's chapter.
        chapter_city = daytime_place_before_overnight or overnight_place or end_place or start_place
        completed_visit = bool(chapter_city and (has_local_content or facts.accommodation_places or day_trip_return))
        transit_only = bool(facts.route_events and not completed_visit)
        explicit_arrival = bool(facts.arrival_places or any("arrival_airport_transfer" in event.flags for event in facts.events))

        first_route_origin = next((event.origin for event in facts.route_events if event.origin), "")
        explicit_rearrival = bool(
            completed_visit
            and chapter_city
            and active_chapter
            and _same_place(chapter_city, active_chapter)
            and first_route_origin
            and not _same_place(first_route_origin, chapter_city)
            and not day_trip_return
        )
        chapter_start = bool(
            completed_visit
            and chapter_city
            and (
                not active_chapter
                or not _same_place(chapter_city, active_chapter)
                or explicit_rearrival
            )
        )
        previous_days = tuple(visits.get(_place_key(chapter_city), ())) if chapter_city else ()
        return_visit = bool(chapter_start and previous_days)
        if chapter_start and chapter_city:
            visits.setdefault(_place_key(chapter_city), []).append(day)
            active_chapter = chapter_city
        visit_number = len(visits.get(_place_key(chapter_city), ())) or 1
        chapter_continuation = bool(completed_visit and not chapter_start and not return_visit)
        same_city_change = bool(
            facts.accommodation_places
            and active_accommodation_place
            and _same_place(facts.accommodation_places[-1], active_accommodation_place)
            and not facts.route_events
        )
        destination_arrival = bool(
            chapter_start
            and not return_visit
            and (explicit_arrival or facts.route_events or facts.accommodation_places)
        )
        arrival_stay = bool(destination_arrival and not facts.route_events)
        stay_continuation = bool(chapter_continuation and not same_city_change)

        states.append(
            DayContinuityState(
                day=day,
                source_row_ids=facts.row_ids,
                start_place=start_place,
                end_place=end_place,
                overnight_place=overnight_place,
                chapter_city=chapter_city,
                visit_number=visit_number,
                previous_visit_days=previous_days,
                transit_cities=_transit_cities(facts, chapter_city),
                completed_visit=completed_visit,
                transit_only=transit_only,
                chapter_start=chapter_start,
                chapter_continuation=chapter_continuation,
                return_visit=return_visit,
                day_trip_return=day_trip_return,
                explicit_arrival=explicit_arrival,
                destination_arrival=destination_arrival,
                arrival_stay=arrival_stay,
                welcome_allowed=arrival_stay,
                same_city_accommodation_change=same_city_change,
                stay_continuation=stay_continuation,
                previous_overnight_place=previous_overnight,
            )
        )
        if end_place:
            established_place = end_place
        elif not established_place:
            established_place = facts.fallback_place
        if overnight_place:
            previous_overnight = overnight_place
        if facts.accommodation_places:
            active_accommodation_place = facts.accommodation_places[-1]
        elif facts.route_events and end_place and active_accommodation_place and not _same_place(end_place, active_accommodation_place):
            active_accommodation_place = ""
        if (
            active_chapter
            and end_place
            and not _same_place(end_place, active_chapter)
            and (transit_only or bool(overnight_route_destination))
        ):
            active_chapter = ""

    return tuple(states)


__all__ = ["_build_day_states"]

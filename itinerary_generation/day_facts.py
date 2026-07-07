"""Fact-only day understanding for deterministic itinerary copy."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from itinerary_generation.common import TRANSPORT_TYPES, get_primary_city, get_row_type, is_optional_row
from itinerary_generation.day_accommodation_facts import (
    confirmed_check_in as _confirmed_check_in,
    confirmed_check_out as _confirmed_check_out,
    ACCOMMODATION_WORDS,
    is_accommodation_change_row,
)
from itinerary_generation.day_accommodation_state import AccommodationState, build_accommodation_state
from itinerary_generation.day_city_facts import (
    add_unique_city,
    arrival_departure_city,
    canonical_city,
    row_text,
)
from itinerary_generation.day_leisure_facts import has_leisure_markers, is_blank_activity_or_leisure
from itinerary_generation.day_schedule_facts import DayScheduleProfile, build_schedule_facts
from itinerary_generation.day_timeline_events import TimelineEvent, normalize_day_events
from itinerary_generation.day_travel_facts import OVERNIGHT_MARKERS, TRAVEL_ROW_TYPES, is_local_transfer, route_points
from itinerary_generation.day_travel_load import TravelLoadProfile, classify_travel_load
from itinerary_generation.day_visit_facts import build_visit_facts

@dataclass(frozen=True)
class DayFacts:
    """Normalized facts about one itinerary day.

    This model must stay prose-free. Writers consume it, but it does not choose
    wording or client-facing phrases.
    """

    rows: tuple[Mapping[str, Any], ...]
    row_types: tuple[str, ...]
    city_sequence: tuple[str, ...] = ()
    route_origins: tuple[str, ...] = ()
    route_destinations: tuple[str, ...] = ()
    hotel_cities: tuple[str, ...] = ()
    activity_cities: tuple[str, ...] = ()
    start_city: str = ""
    end_city: str = ""
    main_city: str = ""
    arrival_city: str = ""
    departure_city: str = ""
    overnight_city: str = ""
    onward_destination: str = ""
    transit_cities: tuple[str, ...] = ()
    has_arrival: bool = False
    has_departure: bool = False
    has_activity: bool = False
    has_accommodation: bool = False
    has_transfer: bool = False
    has_route_transport: bool = False
    has_flight: bool = False
    has_train: bool = False
    has_ferry: bool = False
    has_cruise: bool = False
    has_leisure_row: bool = False
    has_only_leisure_rows: bool = False
    has_local_transfer: bool = False
    has_overnight_transport: bool = False
    confirmed_check_in: bool = False
    confirmed_check_out: bool = False
    same_city_accommodation_change: bool = False
    return_visit: bool = False
    travel_heavy: bool = False
    full_leisure_day: bool = False
    partial_leisure_day: bool = False
    cruise_onboard_day: bool = False
    source_flags: frozenset[str] = field(default_factory=frozenset)
    timeline_events: tuple[TimelineEvent, ...] = ()
    accommodation_state: AccommodationState = field(default_factory=AccommodationState)
    travel_load: TravelLoadProfile = field(default_factory=TravelLoadProfile)
    schedule_profile: DayScheduleProfile = field(default_factory=DayScheduleProfile)
    visit_number: int = 1
    previous_visit_days: tuple[str, ...] = ()

    @property
    def has_travel(self) -> bool:
        return self.has_route_transport or self.has_transfer or self.has_arrival or self.has_departure

    @property
    def route_destination(self) -> str:
        return self.route_destinations[-1] if self.route_destinations else ""

    @property
    def route_origin(self) -> str:
        return self.route_origins[0] if self.route_origins else ""


def build_day_facts(
    rows: Sequence[Mapping[str, Any]] | None,
    *,
    visit_context: object | None = None,
) -> DayFacts:
    """Return normalized day facts without making prose decisions."""

    main_rows = tuple(row for row in (rows or []) if isinstance(row, Mapping) and not is_optional_row(dict(row)))
    row_types = tuple(get_row_type(dict(row)) for row in main_rows)
    timeline_events = normalize_day_events(main_rows)
    accommodation_state = build_accommodation_state(timeline_events)
    travel_load = classify_travel_load(timeline_events)
    schedule_profile = build_schedule_facts(main_rows)
    all_text = " ".join(row_text(row) for row in main_rows).lower()

    city_sequence: list[str] = []
    route_origins: list[str] = []
    route_destinations: list[str] = []
    hotel_cities: list[str] = []
    activity_cities: list[str] = []
    transfer_targets: list[str] = []
    source_flags: set[str] = set()

    has_arrival = has_departure = has_activity = has_accommodation = False
    has_transfer = has_route_transport = has_flight = has_train = False
    has_ferry = has_cruise = has_leisure_row = has_local_transfer = False
    has_overnight_transport = False
    accommodation_change_rows = 0

    for row in main_rows:
        row_type = get_row_type(dict(row))
        text = row_text(row)
        lower = text.lower()
        explicit_city = canonical_city(row.get("city", ""))
        add_unique_city(city_sequence, explicit_city)

        if row_type == "Arrival":
            has_arrival = True
            source_flags.add("arrival")
        elif row_type == "Departure":
            has_departure = True
            source_flags.add("departure")
        elif row_type == "Activity" and not is_blank_activity_or_leisure(row):
            has_activity = True
            source_flags.add("activity")
            add_unique_city(activity_cities, explicit_city)
        elif row_type == "Hotel":
            has_accommodation = True
            source_flags.add("accommodation")
            add_unique_city(hotel_cities, explicit_city)
        elif row_type == "Leisure" or is_blank_activity_or_leisure(row) or (row_type == "Cruise" and has_leisure_markers(lower)):
            has_leisure_row = True
            source_flags.add("leisure")

        if row_type == "Transfer":
            has_transfer = True
            if is_local_transfer(row, accommodation_words=ACCOMMODATION_WORDS):
                has_local_transfer = True
                if explicit_city:
                    transfer_targets.append(explicit_city)
                if "airport" in lower and re.search(r"\b(?:hotel|accommodation|private hotel)\b.*\bto\b", lower):
                    source_flags.add("departure_airport_transfer")
                elif "airport" in lower:
                    source_flags.add("arrival_airport_transfer")

        if row_type in TRAVEL_ROW_TYPES:
            origin, destination = route_points(row)
            if origin:
                add_unique_city(route_origins, origin)
                add_unique_city(city_sequence, origin)
            if destination:
                add_unique_city(route_destinations, destination)
                add_unique_city(city_sequence, destination)
                has_route_transport = True
            if row_type in set(TRANSPORT_TYPES) | {"Transport", "Coach", "Bus"}:
                has_route_transport = has_route_transport or bool(destination or origin)
            if row_type == "Flight":
                has_flight = True
            elif row_type == "Train":
                has_train = True
            elif row_type == "Ferry":
                has_ferry = True
            elif row_type == "Cruise":
                has_cruise = True
            if any(marker in lower for marker in OVERNIGHT_MARKERS):
                has_overnight_transport = True

        if is_accommodation_change_row(row):
            accommodation_change_rows += 1

    primary_city = canonical_city(get_primary_city([dict(row) for row in main_rows]))
    arrival_city = arrival_departure_city(
        main_rows, "Arrival", direction="arrival", primary_city=primary_city, route_origins=route_origins
    )
    departure_city = arrival_departure_city(main_rows, "Departure", direction="departure", primary_city=primary_city)

    overnight_city = hotel_cities[-1] if hotel_cities else ""
    onward_destination = route_destinations[-1] if route_destinations else ""
    end_city = overnight_city or onward_destination or (activity_cities[-1] if activity_cities else "") or primary_city
    start_city = route_origins[0] if route_origins else arrival_city or primary_city or (city_sequence[0] if city_sequence else "")
    main_city = overnight_city or onward_destination or primary_city or start_city

    transit_cities: list[str] = []
    if arrival_city and end_city and arrival_city.casefold() != end_city.casefold():
        add_unique_city(transit_cities, arrival_city)
    for city in city_sequence:
        if city and end_city and city.casefold() != end_city.casefold() and city not in transit_cities:
            if city not in hotel_cities and city not in activity_cities:
                transit_cities.append(city)

    route_count = len(route_destinations)
    non_leisure_rows = [row for row in main_rows if not is_blank_activity_or_leisure(row)]
    has_only_leisure_rows = bool(main_rows) and not non_leisure_rows
    travel_heavy = bool(
        travel_load.is_travel_heavy
        or has_overnight_transport
        or route_count >= 2
        or (has_route_transport and not has_activity and not has_accommodation)
        or (has_route_transport and has_local_transfer and len(main_rows) >= 3)
        or (has_flight and has_transfer)
        or (has_train and has_transfer)
    )
    full_leisure_day = bool(has_only_leisure_rows or (has_leisure_row and not has_activity and not has_route_transport and not has_transfer and not has_accommodation))
    partial_leisure_day = bool(has_leisure_row and not full_leisure_day)
    cruise_onboard_day = bool(has_cruise and has_leisure_row and not has_activity and not has_accommodation and not has_overnight_transport and (has_only_leisure_rows or "onboard" in all_text or "at leisure" in all_text))

    same_city_accommodation_change = bool(
        accommodation_state.same_city_change
        or (
            has_accommodation
            and not has_route_transport
            and "arrival_airport_transfer" not in source_flags
            and "departure_airport_transfer" not in source_flags
            and (has_transfer or accommodation_change_rows >= 2)
            and len(set(hotel_cities or [primary_city])) <= 1
            and not has_arrival
            and not has_departure
        )
    )

    visit_facts = build_visit_facts(visit_context)
    return_visit = visit_facts.return_visit
    visit_number = visit_facts.visit_number
    previous_visit_days = visit_facts.previous_visit_days
    confirmed_check_in = _confirmed_check_in(has_accommodation, same_city_accommodation_change, has_arrival, overnight_city, all_text, accommodation_state)
    confirmed_check_out = _confirmed_check_out(has_accommodation, has_departure, all_text, accommodation_state)
    source_flags.update(accommodation_state.flags)
    source_flags.update(travel_load.flags)
    source_flags.update(schedule_profile.flags)
    if travel_load.level != "none":
        source_flags.add(f"travel_load:{travel_load.level}")

    return DayFacts(
        rows=main_rows,
        row_types=row_types,
        city_sequence=tuple(city_sequence),
        route_origins=tuple(route_origins),
        route_destinations=tuple(route_destinations),
        hotel_cities=tuple(hotel_cities),
        activity_cities=tuple(activity_cities),
        start_city=start_city,
        end_city=end_city,
        main_city=main_city,
        arrival_city=arrival_city,
        departure_city=departure_city,
        overnight_city=overnight_city,
        onward_destination=onward_destination,
        transit_cities=tuple(transit_cities),
        has_arrival=has_arrival,
        has_departure=has_departure,
        has_activity=has_activity,
        has_accommodation=has_accommodation,
        has_transfer=has_transfer,
        has_route_transport=has_route_transport,
        has_flight=has_flight,
        has_train=has_train,
        has_ferry=has_ferry,
        has_cruise=has_cruise,
        has_leisure_row=has_leisure_row,
        has_only_leisure_rows=has_only_leisure_rows,
        has_local_transfer=has_local_transfer,
        has_overnight_transport=has_overnight_transport,
        confirmed_check_in=confirmed_check_in,
        confirmed_check_out=confirmed_check_out,
        same_city_accommodation_change=same_city_accommodation_change,
        return_visit=return_visit,
        travel_heavy=travel_heavy,
        full_leisure_day=full_leisure_day,
        partial_leisure_day=partial_leisure_day,
        cruise_onboard_day=cruise_onboard_day,
        source_flags=frozenset(source_flags),
        timeline_events=timeline_events,
        accommodation_state=accommodation_state,
        travel_load=travel_load,
        schedule_profile=schedule_profile,
        visit_number=visit_number,
        previous_visit_days=previous_visit_days,
    )


__all__ = ["DayFacts", "TRAVEL_ROW_TYPES", "build_day_facts", "row_text"]

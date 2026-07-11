"""Fact-only day understanding for deterministic itinerary copy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from itinerary_generation.common import get_primary_city, get_row_type, is_optional_row
from itinerary_generation.day_accommodation_facts import (
    confirmed_check_in as _confirmed_check_in,
    confirmed_check_out as _confirmed_check_out,
)
from itinerary_generation.day_accommodation_state import AccommodationState, build_accommodation_state
from itinerary_generation.day_city_facts import arrival_departure_city, canonical_city, row_text
from itinerary_generation.day_leisure_facts import is_blank_activity_or_leisure
from itinerary_generation.day_schedule_facts import DayScheduleProfile, build_schedule_facts
from itinerary_generation.day_timeline_events import TimelineEvent, normalize_day_events
from itinerary_generation.day_fact_signals import scan_day_row_signals, transit_cities_for
from itinerary_generation.day_travel_facts import TRAVEL_ROW_TYPES
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
    def has_self_drive(self) -> bool:
        return "Drive" in self.row_types

    @property
    def route_destination(self) -> str:
        return self.route_destinations[-1] if self.route_destinations else ""

    @property
    def route_origin(self) -> str:
        return self.route_origins[0] if self.route_origins else ""



@dataclass(frozen=True)
class _DayCityContext:
    primary_city: str
    arrival_city: str
    departure_city: str
    overnight_city: str
    onward_destination: str
    end_city: str
    start_city: str
    main_city: str
    transit_cities: tuple[str, ...]


@dataclass(frozen=True)
class _DayPatternFlags:
    has_only_leisure_rows: bool
    travel_heavy: bool
    full_leisure_day: bool
    partial_leisure_day: bool
    cruise_onboard_day: bool
    same_city_accommodation_change: bool


def _build_city_context(main_rows, signals, *, primary_city: str) -> _DayCityContext:
    arrival_city = arrival_departure_city(
        main_rows, "Arrival", direction="arrival", primary_city=primary_city, route_origins=signals.route_origins
    )
    departure_city = arrival_departure_city(main_rows, "Departure", direction="departure", primary_city=primary_city)
    overnight_city = signals.hotel_cities[-1] if signals.hotel_cities else ""
    onward_destination = signals.route_destinations[-1] if signals.route_destinations else ""
    end_city = overnight_city or onward_destination or (signals.activity_cities[-1] if signals.activity_cities else "") or primary_city
    start_city = signals.route_origins[0] if signals.route_origins else arrival_city or primary_city or (signals.city_sequence[0] if signals.city_sequence else "")
    main_city = overnight_city or onward_destination or primary_city or start_city
    transit_cities = transit_cities_for(
        city_sequence=signals.city_sequence,
        end_city=end_city,
        arrival_city=arrival_city,
        hotel_cities=signals.hotel_cities,
        activity_cities=signals.activity_cities,
    )
    return _DayCityContext(
        primary_city=primary_city,
        arrival_city=arrival_city,
        departure_city=departure_city,
        overnight_city=overnight_city,
        onward_destination=onward_destination,
        end_city=end_city,
        start_city=start_city,
        main_city=main_city,
        transit_cities=transit_cities,
    )


def _build_day_pattern_flags(main_rows, signals, *, all_text: str, primary_city: str, travel_load, accommodation_state) -> _DayPatternFlags:
    route_count = len(signals.route_destinations)
    non_leisure_rows = [row for row in main_rows if not is_blank_activity_or_leisure(row)]
    has_only_leisure_rows = bool(main_rows) and not non_leisure_rows
    travel_heavy = bool(
        travel_load.is_travel_heavy
        or signals.has_overnight_transport
        or route_count >= 2
        or (signals.has_route_transport and not signals.has_activity and not signals.has_accommodation)
        or (signals.has_route_transport and signals.has_local_transfer and len(main_rows) >= 3)
        or (signals.has_flight and signals.has_transfer)
        or (signals.has_train and signals.has_transfer)
    )
    full_leisure_day = bool(
        has_only_leisure_rows
        or (
            signals.has_leisure_row
            and not signals.has_activity
            and not signals.has_route_transport
            and not signals.has_transfer
            and not signals.has_accommodation
        )
    )
    partial_leisure_day = bool(signals.has_leisure_row and not full_leisure_day)
    cruise_onboard_day = bool(
        signals.has_cruise
        and signals.has_leisure_row
        and not signals.has_activity
        and not signals.has_accommodation
        and not signals.has_overnight_transport
        and (has_only_leisure_rows or "onboard" in all_text or "at leisure" in all_text)
    )
    same_city_accommodation_change = bool(
        accommodation_state.same_city_change
        or (
            signals.has_accommodation
            and not signals.has_route_transport
            and "arrival_airport_transfer" not in signals.source_flags
            and "departure_airport_transfer" not in signals.source_flags
            and (signals.has_transfer or signals.accommodation_change_rows >= 2)
            and len(set(signals.hotel_cities or [primary_city])) <= 1
            and not signals.has_arrival
            and not signals.has_departure
        )
    )
    return _DayPatternFlags(
        has_only_leisure_rows=has_only_leisure_rows,
        travel_heavy=travel_heavy,
        full_leisure_day=full_leisure_day,
        partial_leisure_day=partial_leisure_day,
        cruise_onboard_day=cruise_onboard_day,
        same_city_accommodation_change=same_city_accommodation_change,
    )

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
    signals = scan_day_row_signals(main_rows)

    primary_city = canonical_city(get_primary_city([dict(row) for row in main_rows]))
    city_context = _build_city_context(main_rows, signals, primary_city=primary_city)
    pattern_flags = _build_day_pattern_flags(
        main_rows,
        signals,
        all_text=all_text,
        primary_city=primary_city,
        travel_load=travel_load,
        accommodation_state=accommodation_state,
    )
    visit_facts = build_visit_facts(visit_context)
    confirmed_check_in = _confirmed_check_in(
        signals.has_accommodation,
        pattern_flags.same_city_accommodation_change,
        signals.has_arrival,
        city_context.overnight_city,
        all_text,
        accommodation_state,
    )
    confirmed_check_out = _confirmed_check_out(signals.has_accommodation, signals.has_departure, all_text, accommodation_state)

    source_flags = set(signals.source_flags)
    source_flags.update(accommodation_state.flags)
    source_flags.update(travel_load.flags)
    source_flags.update(schedule_profile.flags)
    if travel_load.level != "none":
        source_flags.add(f"travel_load:{travel_load.level}")

    return DayFacts(
        rows=main_rows,
        row_types=row_types,
        city_sequence=tuple(signals.city_sequence),
        route_origins=tuple(signals.route_origins),
        route_destinations=tuple(signals.route_destinations),
        hotel_cities=tuple(signals.hotel_cities),
        activity_cities=tuple(signals.activity_cities),
        start_city=city_context.start_city,
        end_city=city_context.end_city,
        main_city=city_context.main_city,
        arrival_city=city_context.arrival_city,
        departure_city=city_context.departure_city,
        overnight_city=city_context.overnight_city,
        onward_destination=city_context.onward_destination,
        transit_cities=city_context.transit_cities,
        has_arrival=signals.has_arrival,
        has_departure=signals.has_departure,
        has_activity=signals.has_activity,
        has_accommodation=signals.has_accommodation,
        has_transfer=signals.has_transfer,
        has_route_transport=signals.has_route_transport,
        has_flight=signals.has_flight,
        has_train=signals.has_train,
        has_ferry=signals.has_ferry,
        has_cruise=signals.has_cruise,
        has_leisure_row=signals.has_leisure_row,
        has_only_leisure_rows=pattern_flags.has_only_leisure_rows,
        has_local_transfer=signals.has_local_transfer,
        has_overnight_transport=signals.has_overnight_transport,
        confirmed_check_in=confirmed_check_in,
        confirmed_check_out=confirmed_check_out,
        same_city_accommodation_change=pattern_flags.same_city_accommodation_change,
        return_visit=visit_facts.return_visit,
        travel_heavy=pattern_flags.travel_heavy,
        full_leisure_day=pattern_flags.full_leisure_day,
        partial_leisure_day=pattern_flags.partial_leisure_day,
        cruise_onboard_day=pattern_flags.cruise_onboard_day,
        source_flags=frozenset(source_flags),
        timeline_events=timeline_events,
        accommodation_state=accommodation_state,
        travel_load=travel_load,
        schedule_profile=schedule_profile,
        visit_number=visit_facts.visit_number,
        previous_visit_days=visit_facts.previous_visit_days,
    )


__all__ = ["DayFacts", "TRAVEL_ROW_TYPES", "build_day_facts", "row_text"]

"""Row-scan signals used to build prose-free day facts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from itinerary_generation.airport_transfer_contract import airport_transfer_facts
from itinerary_generation.common import TRANSPORT_TYPES, get_row_type
from itinerary_generation.day_accommodation_facts import ACCOMMODATION_WORDS, is_accommodation_change_row
from itinerary_generation.day_city_facts import add_unique_city, canonical_city, row_text
from itinerary_generation.day_leisure_facts import has_leisure_markers, is_blank_activity_or_leisure
from itinerary_generation.day_travel_facts import OVERNIGHT_MARKERS, TRAVEL_ROW_TYPES, is_local_transfer, transport_endpoints


@dataclass
class DayRowSignals:
    """Mutable scan result collected from raw itinerary rows.

    The object deliberately contains facts and flags only. It must not contain
    prose, copy templates, or render decisions.
    """

    city_sequence: list[str] = field(default_factory=list)
    route_origins: list[str] = field(default_factory=list)
    route_destinations: list[str] = field(default_factory=list)
    hotel_cities: list[str] = field(default_factory=list)
    activity_cities: list[str] = field(default_factory=list)
    source_flags: set[str] = field(default_factory=set)
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
    has_local_transfer: bool = False
    has_overnight_transport: bool = False
    accommodation_change_rows: int = 0


_ROUTE_TRANSPORT_TYPES = set(TRANSPORT_TYPES) | {"Transport", "Coach", "Bus"}


def _scan_arrival_departure(row_type: str, signals: DayRowSignals) -> None:
    if row_type == "Arrival":
        signals.has_arrival = True
        signals.source_flags.add("arrival")
    elif row_type == "Departure":
        signals.has_departure = True
        signals.source_flags.add("departure")


def _scan_activity_accommodation_leisure(
    row: Mapping[str, Any],
    *,
    row_type: str,
    lower_text: str,
    explicit_city: str,
    signals: DayRowSignals,
) -> None:
    if row_type == "Activity" and not is_blank_activity_or_leisure(row):
        signals.has_activity = True
        signals.source_flags.add("activity")
        add_unique_city(signals.activity_cities, explicit_city)
    elif row_type == "Hotel":
        signals.has_accommodation = True
        signals.source_flags.add("accommodation")
        add_unique_city(signals.hotel_cities, explicit_city)
    elif row_type == "Leisure" or is_blank_activity_or_leisure(row) or (row_type == "Cruise" and has_leisure_markers(lower_text)):
        signals.has_leisure_row = True
        signals.source_flags.add("leisure")


def _scan_transfer(
    row: Mapping[str, Any],
    *,
    row_type: str,
    lower_text: str,
    explicit_city: str,
    signals: DayRowSignals,
) -> None:
    if row_type != "Transfer":
        return
    signals.has_transfer = True
    airport_facts = airport_transfer_facts(row)
    if airport_facts.direction == "departure":
        signals.source_flags.add("departure_airport_transfer")
    elif airport_facts.direction == "arrival":
        signals.source_flags.add("arrival_airport_transfer")
    elif airport_facts.is_airport_transfer:
        signals.source_flags.add("airport_transfer_direction_unknown")
    if not is_local_transfer(row, accommodation_words=ACCOMMODATION_WORDS):
        return
    signals.has_local_transfer = True
    if explicit_city:
        add_unique_city(signals.city_sequence, explicit_city)


def _scan_route_transport(row: Mapping[str, Any], *, row_type: str, lower_text: str, signals: DayRowSignals) -> None:
    if row_type not in TRAVEL_ROW_TYPES:
        return

    origin, destination = transport_endpoints(row)
    if origin:
        add_unique_city(signals.route_origins, origin)
        add_unique_city(signals.city_sequence, origin)
    if destination:
        add_unique_city(signals.route_destinations, destination)
        add_unique_city(signals.city_sequence, destination)
        signals.has_route_transport = True
    if row_type in _ROUTE_TRANSPORT_TYPES:
        signals.has_route_transport = signals.has_route_transport or bool(destination or origin)
    if row_type == "Flight":
        signals.has_flight = True
    elif row_type == "Train":
        signals.has_train = True
    elif row_type == "Ferry":
        signals.has_ferry = True
    elif row_type == "Cruise":
        signals.has_cruise = True
    if any(marker in lower_text for marker in OVERNIGHT_MARKERS):
        signals.has_overnight_transport = True


def scan_day_row_signals(rows: Sequence[Mapping[str, Any]]) -> DayRowSignals:
    """Collect normalized day-level booleans, cities, routes, and flags."""

    signals = DayRowSignals()
    for row in rows:
        row_type = get_row_type(dict(row))
        text = row_text(row)
        lower_text = text.lower()
        explicit_city = canonical_city(row.get("city", ""))
        add_unique_city(signals.city_sequence, explicit_city)

        _scan_arrival_departure(row_type, signals)
        _scan_activity_accommodation_leisure(
            row,
            row_type=row_type,
            lower_text=lower_text,
            explicit_city=explicit_city,
            signals=signals,
        )
        _scan_transfer(
            row,
            row_type=row_type,
            lower_text=lower_text,
            explicit_city=explicit_city,
            signals=signals,
        )
        _scan_route_transport(row, row_type=row_type, lower_text=lower_text, signals=signals)

        if is_accommodation_change_row(row):
            signals.accommodation_change_rows += 1
    return signals


def transit_cities_for(
    *,
    city_sequence: Sequence[str],
    end_city: str,
    arrival_city: str,
    hotel_cities: Sequence[str],
    activity_cities: Sequence[str],
) -> tuple[str, ...]:
    """Return safe transit-only cities for a day."""

    transit_cities: list[str] = []
    if arrival_city and end_city and arrival_city.casefold() != end_city.casefold():
        add_unique_city(transit_cities, arrival_city)
    for city in city_sequence:
        if not city or not end_city or city.casefold() == end_city.casefold() or city in transit_cities:
            continue
        if city not in hotel_cities and city not in activity_cities:
            transit_cities.append(city)
    return tuple(transit_cities)


__all__ = ["DayRowSignals", "scan_day_row_signals", "transit_cities_for"]

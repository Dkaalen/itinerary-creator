"""Deterministic day-intent classification for itinerary copy."""

from __future__ import annotations

from enum import StrEnum

from itinerary_generation.day_facts import DayFacts


class DayIntent(StrEnum):
    ARRIVAL_STAY = "arrival_stay"
    ARRIVAL_ONWARD_TRAVEL = "arrival_onward_travel"
    CITY_STAY = "city_stay"
    ACTIVITY_DAY = "activity_day"
    ACTIVITY_PLUS_TRAVEL = "activity_plus_travel"
    TRAVEL_DAY = "travel_day"
    SAME_CITY_ACCOMMODATION_CHANGE = "same_city_accommodation_change"
    RETURN_VISIT = "return_visit"
    FULL_LEISURE_DAY = "full_leisure_day"
    PARTIAL_LEISURE_DAY = "partial_leisure_day"
    DEPARTURE_DAY = "departure_day"
    OVERNIGHT_TRANSPORT_DAY = "overnight_transport_day"
    CRUISE_DAY = "cruise_day"


def classify_day_intent(facts: DayFacts) -> DayIntent:
    """Classify one day using facts only."""

    state = facts.day_state
    if (facts.has_departure or "departure_airport_transfer" in facts.source_flags) and not facts.has_activity and not facts.has_accommodation:
        return DayIntent.DEPARTURE_DAY
    if state.same_city_accommodation_change:
        return DayIntent.SAME_CITY_ACCOMMODATION_CHANGE
    if state.return_visit and not facts.has_activity and (state.explicit_arrival or facts.has_route_transport or facts.has_accommodation):
        return DayIntent.RETURN_VISIT
    if state.arrival_onward:
        return DayIntent.ARRIVAL_ONWARD_TRAVEL
    if state.arrival_stay and facts.has_activity:
        return DayIntent.ACTIVITY_PLUS_TRAVEL
    if state.arrival_stay:
        return DayIntent.ARRIVAL_STAY
    if (
        facts.has_route_transport
        and facts.has_accommodation
        and facts.end_city
        and facts.main_city
        and facts.end_city.casefold() == facts.main_city.casefold()
    ):
        if facts.has_activity:
            return DayIntent.ACTIVITY_PLUS_TRAVEL
        # An explicit intercity route remains a travel day even when it ends at
        # the night's accommodation. Arrival-stay wording is reserved for a
        # real arrival event or airport-arrival transfer handled above.
        return DayIntent.TRAVEL_DAY
    if facts.has_activity and facts.has_travel:
        return DayIntent.ACTIVITY_PLUS_TRAVEL
    if facts.has_overnight_transport:
        return DayIntent.OVERNIGHT_TRANSPORT_DAY
    if facts.cruise_onboard_day or (facts.has_cruise and facts.has_leisure_row and not facts.has_activity):
        return DayIntent.CRUISE_DAY
    if facts.full_leisure_day:
        return DayIntent.FULL_LEISURE_DAY
    if facts.has_route_transport:
        return DayIntent.TRAVEL_DAY
    if facts.has_activity:
        return DayIntent.ACTIVITY_DAY
    if facts.partial_leisure_day:
        return DayIntent.PARTIAL_LEISURE_DAY
    return DayIntent.CITY_STAY


__all__ = ["DayIntent", "classify_day_intent"]

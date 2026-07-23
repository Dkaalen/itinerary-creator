"""Intent-to-phrase selection for fact-based day intros."""
from __future__ import annotations

import re

from itinerary_generation.client_text_decisions import client_activity_intro, client_group_tour_intro
from itinerary_generation.common import get_activity_text, get_row_type
from itinerary_generation.content_engine import is_supplier_day_row
from itinerary_generation.day_activity_text import get_client_activity_phrase
from itinerary_generation.day_facts import DayFacts, row_text
from itinerary_generation.day_intent import DayIntent, classify_day_intent
from itinerary_generation.day_intro_context import (
    _activity_rows, _city, _clean, _has_port_transfer, _has_station_transfer,
    _main_city, _mode, _travel_phrase,
)
from itinerary_generation.day_intro_destination_context import _arrival_stay_intro, _destination_identity
from itinerary_generation.day_intro_repetition import _return_visit_intro
from itinerary_generation.transport_domain.route_summary import transport_endpoints_from_row
from itinerary_generation.transport_domain.client_wording import build_day_client_transport_wording
from itinerary_generation.day_route_text import create_travel_route_label
from itinerary_generation.route_intelligence import route_intro_for_day


def _departure_transfer_intro(facts: DayFacts) -> str:
    text = " ".join(row_text(row) for row in facts.rows)
    lower = text.lower()
    if "airport" not in lower and not any(marker in lower for marker in ("self transfer", "self-arranged", "self arranged", "own way")):
        return ""
    match = re.search(r"\bto\s+([A-ZÀ-Ý][A-Za-zÀ-ÿøØåÅäÄöÖ .'-]*?Airport)\b", text)
    airport = _clean(match.group(1)) if match else "the airport"
    if facts.has_self_drive:
        rental_clause = " Return your rental vehicle before continuing with your onward journey." if re.search(r"\b(?:rental|hire)\s+(?:car|vehicle)|return\s+(?:the\s+)?(?:car|vehicle)", lower) else " Continue with your onward journey after returning the vehicle."
        return f"After check-out, drive to {airport}.{rental_clause}"
    if any(marker in lower for marker in ("self transfer", "self-arranged", "self arranged", "own way")):
        return f"After check-out, please make your own way to {airport} for your onward journey."
    route_rows = [row for row in facts.rows if get_row_type(dict(row)) == "Transfer"]
    if len(route_rows) == 1:
        origin, destination = transport_endpoints_from_row(dict(route_rows[0]))
        if origin and destination and "airport" in destination.casefold():
            return f"After check-out, take your arranged transfer from {origin} to {destination} for your onward journey."
    return f"Your arranged transfer will take you from your hotel to {airport} for your onward journey."


def _route_intro(facts: DayFacts) -> str:
    intro = route_intro_for_day([dict(row) for row in facts.rows])
    return _clean(intro)


def _profile_route_intro(facts: DayFacts) -> str:
    # Self-drive prose is owned by Day Brain so route profiles cannot replace
    # clear "Drive from ... to ..." or return-visit wording.
    if facts.has_self_drive:
        return ""
    combined_text = " ".join(row_text(row) for row in facts.rows).lower()
    if "tallinn" in combined_text:
        return ""
    if "norway in a nutshell" in combined_text:
        destination = _city(facts.end_city or facts.main_city or facts.route_destination) or "the destination"
        return (
            f"Follow the Norway in a Nutshell route towards {destination}, with the rail, "
            "fjord and road segments presented together as one signature scenic journey."
        )

    intro = _route_intro(facts)
    lower_intro = intro.lower()
    if not intro:
        return ""
    generic_markers = (
        "with the planned travel arrangements",
        "self transfer",
    )
    if any(marker in lower_intro for marker in generic_markers):
        return ""
    return intro


def _activity_intro(facts: DayFacts) -> str:
    activities = _activity_rows(facts)
    combined_text = " ".join(row_text(row) for row in facts.rows).lower()
    if "tallinn" in combined_text:
        if facts.has_overnight_transport or "overnight train" in combined_text:
            return (
                "Cross from Helsinki to Tallinn for a memorable day trip, with time to experience "
                "the historic Old Town before returning to Helsinki for your overnight train north."
            )
        return (
            "Cross from Helsinki to Tallinn for a memorable day trip, with time to experience "
            "the historic Old Town before returning to Helsinki for the next stage of the trip."
        )

    city = _main_city(facts) or "the experience area"
    if not activities:
        return f"The day’s included arrangements in {city} are listed below." if city else "The day’s included arrangements are listed below."
    first = dict(activities[0])
    activity_city = _city(first.get("city", ""))
    if activity_city and (facts.has_overnight_transport or (city and activity_city.casefold() != city.casefold())):
        city = activity_city
    title = get_client_activity_phrase(first)
    source_text = get_activity_text(first)
    if is_supplier_day_row(first):
        supplier_city = _clean(first.get("city")) or city
        return client_group_tour_intro(title, supplier_city, source_text)
    return client_activity_intro(title, city, source_text)


def _scheduled_activity_intro(facts: DayFacts) -> str:
    schedule = facts.schedule_profile
    if not schedule.has_multiple_arranged_activities:
        return ""
    city = _main_city(facts) or "the area"
    first = schedule.first_activity_title or "the first included experience"
    last = schedule.last_activity_title or "the later included experience"
    source_text = " ".join(row_text(row) for row in facts.rows)
    combined_title = f"{first} and {last}" if first != last else first
    if schedule.has_morning_activity and schedule.has_evening_activity:
        return f"Today is built around {first}, followed by {last} later on, with the time between them kept light and easy."
    if schedule.has_evening_activity:
        return f"Begin with {first} at your own pace, then join {last} later in the day, with the schedule kept flexible between the two experiences."
    composed_intro = client_activity_intro(combined_title, city, source_text)
    if "main arranged experience" not in composed_intro:
        return composed_intro
    return f"Today includes multiple arranged experiences in {city}, with the timing and details listed below."


def _arrival_onward_intro(facts: DayFacts) -> str:
    arrival = _city(facts.arrival_city or facts.start_city) or "your arrival point"
    destination = _city(facts.onward_destination or facts.end_city) or "the next destination"
    connector = "continue"
    if _has_station_transfer(facts):
        connector = "continue to the central station"
    elif _has_port_transfer(facts):
        connector = "continue to the port"
    mode = _mode(facts)
    travel_label = f"overnight {mode}" if facts.has_overnight_transport and mode in {"train", "ferry", "cruise"} else mode
    if destination and destination.casefold() != arrival.casefold():
        return f"Arrive in {arrival} and {connector} for the {travel_label} to {destination}."
    return f"Arrive in {arrival} and continue with the onward travel arrangements listed below."


def select_day_intro_text(facts: DayFacts, intent: DayIntent | None = None) -> str:
    """Return intro copy after day facts have been classified."""

    intent = intent or classify_day_intent(facts)
    city = _main_city(facts)

    if intent == DayIntent.ARRIVAL_ONWARD_TRAVEL:
        return _arrival_onward_intro(facts)

    if intent == DayIntent.SAME_CITY_ACCOMMODATION_CHANGE:
        place = city or "the same destination"
        return f"Today you move to your next stay in {place}, with the transfer and accommodation details listed below."

    profile_route_intro = _profile_route_intro(facts)
    if profile_route_intro and intent in {
        DayIntent.ARRIVAL_STAY,
        DayIntent.TRAVEL_DAY,
        DayIntent.CRUISE_DAY,
    }:
        suppress_arrival_route_intro = intent == DayIntent.ARRIVAL_STAY and (
            facts.has_flight or "arrival_airport_transfer" in facts.source_flags
        )
        if not suppress_arrival_route_intro:
            return profile_route_intro

    if intent == DayIntent.RETURN_VISIT:
        return _return_visit_intro(facts, profile_route_intro, city)

    if intent == DayIntent.DEPARTURE_DAY:
        departure_transfer = _departure_transfer_intro(facts)
        if departure_transfer:
            return departure_transfer
        return "Your arrangements conclude today with the departure details listed below."

    if intent == DayIntent.OVERNIGHT_TRANSPORT_DAY:
        route_label = create_travel_route_label([dict(row) for row in facts.rows])
        if route_label:
            return f"Travel from {route_label}, with the overnight journey and onboard arrangements listed below."
        wording = build_day_client_transport_wording([dict(row) for row in facts.rows])
        if wording is not None and wording.travel_phrase:
            return f"{wording.travel_phrase}, with the journey and onboard arrangements listed below."
        travel = _travel_phrase(facts).replace("Travel", "Travel overnight", 1)
        return f"{travel}, with the journey and onboard arrangements listed below."

    if intent == DayIntent.CRUISE_DAY:
        route_intro = _route_intro(facts)
        if route_intro:
            return route_intro
        if facts.route_origin or facts.route_destination:
            return f"{_travel_phrase(facts)} today, with the coastal cruise and onboard arrangements forming the focus of the day."
        return "Spend the day onboard, with the sailing and onboard arrangements forming the focus of the day."

    if intent == DayIntent.ARRIVAL_STAY:
        return _arrival_stay_intro(facts, city)

    if intent == DayIntent.ACTIVITY_PLUS_TRAVEL:
        scheduled_intro = _scheduled_activity_intro(facts)
        if scheduled_intro:
            return scheduled_intro
        activity_text = _activity_intro(facts)
        if facts.day_state.destination_arrival:
            place = city or "the destination"
            activities = _activity_rows(facts)
            if activities:
                title = get_client_activity_phrase(dict(activities[0]))
                if facts.day_state.welcome_allowed:
                    return f"Welcome to {place}. After arrival, the day includes {title}, with the details listed below."
                return f"Arrive in {place} today before {title}, with the confirmed travel and activity details listed below."
            return f"Arrive in {place} today before the included experience listed below."
        if facts.has_accommodation and city and facts.day_state.welcome_allowed:
            return f"Welcome to {city}. After arrival, settle into the logistics first, then continue into the included experience later today."
        return activity_text

    if intent == DayIntent.TRAVEL_DAY:
        if facts.has_self_drive:
            return f"{_travel_phrase(facts)}, with the route and key logistics listed below."
        route_intro = _route_intro(facts)
        if route_intro:
            return route_intro
        return f"{_travel_phrase(facts)}, with the route and key logistics listed below."

    if intent == DayIntent.ACTIVITY_DAY:
        scheduled_intro = _scheduled_activity_intro(facts)
        if scheduled_intro:
            return scheduled_intro
        return _activity_intro(facts)

    if intent == DayIntent.FULL_LEISURE_DAY:
        place = city or "the destination"
        return f"A full day is left open in {place}, with no arranged activities competing for your time."

    if intent == DayIntent.PARTIAL_LEISURE_DAY:
        place = city or "the area"
        return f"This day in {place} leaves some time flexible around the listed arrangements."

    if city:
        if facts.has_accommodation and facts.day_state.welcome_allowed:
            identity = _destination_identity(city)
            return f"Welcome to {city}. The day stays relaxed around your stay, with time to get a feel for {identity}."
        if facts.has_accommodation:
            return f"Continue your stay in {city}, with today’s accommodation arrangements kept clear and easy to follow."
        return f"This is part of your stay in {city}, with today’s plans kept clear and easy to follow."
    return "The day’s arrangements are listed below."

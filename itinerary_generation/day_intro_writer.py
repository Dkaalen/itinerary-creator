"""Fact-based intro copy writer for itinerary days."""

from __future__ import annotations

import re
from typing import Any, Mapping

from itinerary_generation.client_text_decisions import client_activity_intro, client_group_tour_intro
from itinerary_generation.copy_decision_contract import CopyDecisionTrace, decision_candidate, finalize_decision
from itinerary_generation.common import get_activity_text, get_row_type
from itinerary_generation.content_engine import is_supplier_day_row
from itinerary_generation.day_activity_text import get_client_activity_phrase
from itinerary_generation.day_facts import DayFacts, row_text
from itinerary_generation.day_intent import DayIntent, classify_day_intent
from itinerary_generation.transport_domain.route_summary import transport_endpoints_from_row
from itinerary_generation.day_route_text import create_travel_route_label
from itinerary_generation.day_leisure_writer import write_leisure_copy
from itinerary_generation.destination_profile_builder import destination_profile_for
from itinerary_generation.route_intelligence import route_intro_for_day
from place_aliases import country_for_place
from shared.text import clean_space
from text_polish import polish_title


def _clean(value: object) -> str:
    return clean_space(value)


def _city(value: object) -> str:
    return polish_title(_clean(value))


def _main_city(facts: DayFacts) -> str:
    return _city(facts.main_city or facts.end_city or facts.overnight_city or facts.arrival_city or facts.start_city)


def _mode(facts: DayFacts) -> str:
    if facts.has_self_drive:
        return "self-drive route"
    if facts.has_overnight_transport and facts.has_cruise:
        return "cruise"
    if facts.has_overnight_transport and facts.has_train:
        return "train"
    if facts.has_flight:
        return "flight"
    if facts.has_train:
        return "train"
    if facts.has_ferry:
        return "ferry"
    if facts.has_cruise:
        return "cruise"
    return "transfer" if facts.has_transfer else "travel"


def _travel_phrase(facts: DayFacts, *, imperative: bool = False) -> str:
    origin = _city(facts.route_origin or facts.start_city)
    destination = _city(facts.route_destination or facts.end_city or facts.onward_destination)
    if facts.has_self_drive:
        verb = "Continue driving" if imperative else "Drive"
        if origin and destination and origin.casefold() != destination.casefold():
            return f"{verb} from {origin} to {destination}"
        if destination:
            return f"{verb} to {destination}"
        return f"{verb} along the listed route"
    mode = _mode(facts)
    verb = "Continue" if imperative else "Travel"
    if origin and destination and origin.casefold() != destination.casefold():
        return f"{verb} from {origin} to {destination} by {mode}"
    if destination:
        return f"{verb} to {destination} by {mode}"
    return f"{verb} with the listed travel arrangements"


def _has_station_transfer(facts: DayFacts) -> bool:
    text = " ".join(row_text(row) for row in facts.rows).lower()
    return any(marker in text for marker in ("central station", "railway station", "train station", "station"))


def _has_port_transfer(facts: DayFacts) -> bool:
    text = " ".join(row_text(row) for row in facts.rows).lower()
    return any(marker in text for marker in ("cruise terminal", "ferry terminal", "harbour", "harbor", "port"))


def _activity_rows(facts: DayFacts) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    for row in facts.rows:
        if get_row_type(dict(row)) != "Activity":
            continue
        text = row_text(row).lower()
        if "leisure" in text or "free time" in text:
            continue
        rows.append(row)
    return rows


def _destination_identity(city: str) -> str:
    profile = destination_profile_for(city)
    return profile.arrival_identity or profile.identity or city


def _arrival_display_place(facts: DayFacts, city: str) -> str:
    if "arrival_airport_transfer" in facts.source_flags and country_for_place(city) == "Iceland":
        return "Iceland"
    return city


def _arrival_transfer_clause(facts: DayFacts) -> str:
    """Return a client-facing arrival logistics clause, not admin/report copy."""

    text = " ".join(row_text(row) for row in facts.rows).lower()
    if "flybus" in text:
        return "the arranged Flybus transfer brings you towards your accommodation area"
    if "self transfer" in text or "self-transfer" in text or "self arranged" in text or "self-arranged" in text:
        return "follow the self-arranged transfer details to reach your accommodation"
    if facts.has_transfer:
        return "your arranged transfer brings you to your accommodation"
    return "the schedule is kept simple around your arrival"


def _arrival_stay_intro(facts: DayFacts, city: str) -> str:
    place = _arrival_display_place(facts, city or "the destination") if city else "the destination"
    identity = _destination_identity(city or place)
    if facts.return_visit:
        return f"Return to {place}. After arrival, the day stays light so you can settle back in around the listed arrangements."
    transfer_clause = _arrival_transfer_clause(facts)
    if facts.has_transfer or facts.has_flight:
        return f"Welcome to {place}. After arrival, {transfer_clause}, then the rest of the day stays light so you can settle in and get a feel for {identity}."
    return f"Welcome to {place}. The day stays light, with time to settle in and get a feel for {identity}."


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


def _return_visit_intro(facts: DayFacts, profile_route_intro: str, city: str) -> str:
    """Describe a return stay from route truth instead of admin fallback copy."""

    place = city or _city(facts.end_city) or "the destination"
    destinations = [_city(item) for item in facts.route_destinations if _city(item)]
    round_trip = bool(
        place
        and len(destinations) >= 2
        and destinations[-1].casefold() == place.casefold()
        and any(item.casefold() != place.casefold() for item in destinations[:-1])
    )
    if round_trip:
        return (
            f"Head out on today’s planned journey before returning to {place}, "
            "with the travel timings and overnight stay kept together below."
        )
    if facts.has_self_drive:
        origin = _city(facts.route_origin or facts.start_city)
        if origin and origin.casefold() != place.casefold():
            return f"Drive from {origin} back to {place}, with the route and overnight stay forming the focus of the day."
        return f"Drive back to {place}, with the route and overnight stay forming the focus of the day."
    if profile_route_intro:
        return profile_route_intro
    if facts.has_travel:
        if facts.has_activity:
            return f"Return to {place}, with the onward route and included experience arranged together."
        return f"Return to {place}. The journey and arrival at your next stay are kept straightforward below."
    return f"Back in {place}, the day continues around the arrangements already confirmed for your stay."


def _write_day_intro_text(facts: DayFacts, intent: DayIntent | None = None) -> str:
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
        if facts.has_arrival:
            place = city or "the destination"
            activities = _activity_rows(facts)
            if activities:
                title = get_client_activity_phrase(dict(activities[0]))
                return f"Welcome to {place}. After arrival, the day includes {title}, with the details listed below."
            return f"Arrive in {place} today before the included experience listed below."
        if facts.has_accommodation and city and not facts.return_visit:
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
        if facts.has_accommodation and not facts.return_visit:
            identity = _destination_identity(city)
            return f"Welcome to {city}. The day stays relaxed around your stay, with time to get a feel for {identity}."
        return f"This is part of your stay in {city}, with today’s plans kept clear and easy to follow."
    return "The day’s arrangements are listed below."


def _intro_source_for(facts: DayFacts, intent: DayIntent, intro: str) -> tuple[str, str, int, tuple[str, ...]]:
    """Classify the selected intro source without creating a second prose owner."""

    lowered = intro.casefold()
    if intent == DayIntent.ARRIVAL_ONWARD_TRAVEL:
        return "arrival_onward_intro", "Arrival plus onward-travel intent owns this intro.", 86, ()
    if intent == DayIntent.SAME_CITY_ACCOMMODATION_CHANGE:
        return "accommodation_change_intro", "Same-city accommodation-change intent owns this intro.", 76, ()
    if "norway in a nutshell" in lowered or "signature scenic journey" in lowered:
        return "profile_route_intro", "Route profile owns this scenic-journey intro.", 90, ()
    if intent == DayIntent.RETURN_VISIT:
        return "return_visit_intro", "Visit context marks this as a return stay.", 80, ()
    if intent == DayIntent.DEPARTURE_DAY:
        return "departure_intro", "Departure-day intent owns this intro.", 82, ()
    if intent == DayIntent.OVERNIGHT_TRANSPORT_DAY:
        return "overnight_transport_intro", "Overnight transport intent owns this intro.", 86, ()
    if intent == DayIntent.CRUISE_DAY:
        return "cruise_day_intro", "Cruise-day facts own this intro.", 86, ()
    if intent == DayIntent.ARRIVAL_STAY:
        return "arrival_stay_intro", "Arrival-stay facts own this intro.", 86, ()
    if intent == DayIntent.ACTIVITY_PLUS_TRAVEL:
        return "activity_plus_travel_intro", "Travel plus activity facts own this intro.", 86, ()
    if intent == DayIntent.TRAVEL_DAY:
        return "travel_day_intro", "Transport facts own this intro.", 84, ()
    if intent == DayIntent.ACTIVITY_DAY:
        return "activity_day_intro", "Activity facts own this intro.", 84, ()
    if intent == DayIntent.FULL_LEISURE_DAY:
        return "full_leisure_intro", "Full-leisure intent owns a distinct day-level introduction.", 82, ()
    if intent == DayIntent.PARTIAL_LEISURE_DAY:
        return "partial_leisure_intro", "Partial-leisure intent owns this intro.", 74, ()
    if "arrangements are listed below" in lowered or "listed below" in lowered:
        return "admin_fallback_intro", "Fallback/admin-style intro remained after stronger branches missed.", 20, ("fallback_intro",)
    return "contextual_day_intro", "Day facts selected contextual intro copy.", 70, ()


def plan_day_intro_decision(facts: DayFacts, intent: DayIntent | None = None) -> CopyDecisionTrace:
    """Return intro copy with traceable intent/source metadata."""

    intent = intent or classify_day_intent(facts)
    intro = _write_day_intro_text(facts, intent)
    source, reason, priority, risk_flags = _intro_source_for(facts, intent, intro)
    selected = decision_candidate(intro, source=source, priority=priority, reason=reason, risk_flags=risk_flags)
    assert selected is not None
    return finalize_decision(
        kind="day_intro",
        selected=selected,
        context={
            "intent": getattr(intent, "name", str(intent)),
            "city": _main_city(facts),
        },
    )


def write_day_intro(facts: DayFacts, intent: DayIntent | None = None) -> str:
    """Return intro copy after day facts have been classified."""

    return plan_day_intro_decision(facts, intent).text


__all__ = ["plan_day_intro_decision", "write_day_intro"]

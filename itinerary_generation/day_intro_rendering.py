"""Decision metadata and final rendering contract for day intros."""
from __future__ import annotations

from itinerary_generation.copy_decision_contract import CopyDecisionTrace, decision_candidate, finalize_decision
from itinerary_generation.day_facts import DayFacts
from itinerary_generation.day_intent import DayIntent, classify_day_intent
from itinerary_generation.day_intro_context import _main_city
from itinerary_generation.day_intro_phrase_selection import select_day_intro_text
from itinerary_generation.day_intro_seasonal_context import seasonal_context_for


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
    intent = intent or classify_day_intent(facts)
    intro = select_day_intro_text(facts, intent)
    source, reason, priority, risk_flags = _intro_source_for(facts, intent, intro)
    selected = decision_candidate(intro, source=source, priority=priority, reason=reason, risk_flags=risk_flags)
    assert selected is not None
    season = seasonal_context_for(facts)
    return finalize_decision(
        kind="day_intro",
        selected=selected,
        context={
            "intent": getattr(intent, "name", str(intent)),
            "city": _main_city(facts),
            "season": season.season,
            "season_source_date": season.source_date,
        },
    )


def write_day_intro(facts: DayFacts, intent: DayIntent | None = None) -> str:
    return plan_day_intro_decision(facts, intent).text

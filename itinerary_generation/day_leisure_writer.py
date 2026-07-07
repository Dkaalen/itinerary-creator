"""Context-aware leisure/free-time copy writer."""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from itinerary_generation.day_facts import DayFacts, build_day_facts
from itinerary_generation.day_copy_variation import choose_copy_variant
from itinerary_generation.day_intent import DayIntent, classify_day_intent
from text_polish import polish_title


def _clean_city(value: object) -> str:
    return polish_title(str(value or "").strip())


def _fallback_city(facts: DayFacts) -> str:
    return _clean_city(facts.main_city or facts.end_city or facts.start_city or "the area")


def _sentence(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def write_leisure_copy(facts: DayFacts, intent: DayIntent | None = None) -> str:
    """Return free-time copy from day facts and intent."""

    intent = intent or classify_day_intent(facts)
    city = _fallback_city(facts)

    if intent == DayIntent.CRUISE_DAY or facts.cruise_onboard_day:
        return _sentence(choose_copy_variant((
            "Time onboard is open for you to enjoy the sailing, the ship facilities and the coastal views as the route continues.",
            "Your time onboard remains flexible, with space to enjoy the ship facilities and the changing coastal views.",
            "Onboard time is left open for the sailing itself, the ship facilities and the views along the route.",
        ), facts, intent))

    if facts.travel_heavy or intent in {DayIntent.TRAVEL_DAY, DayIntent.OVERNIGHT_TRANSPORT_DAY, DayIntent.ARRIVAL_ONWARD_TRAVEL}:
        return "Any free time today is limited and flexible around the travel arrangements."

    if intent == DayIntent.FULL_LEISURE_DAY or facts.full_leisure_day:
        if city and city != "the area":
            return _sentence(
                f"Today is open for independent time in {city}. "
                "You may explore locally, keep the pace relaxed, or simply enjoy a quieter day between arranged experiences."
            )
        return "Today is open for independent time, with space to rest, explore locally or keep the pace flexible."

    schedule = facts.schedule_profile
    if schedule.has_multiple_arranged_activities and (schedule.has_leisure_between_activities or schedule.has_activity_after_leisure or schedule.has_gap_between_activities):
        return choose_copy_variant((
            "Between today’s arranged experiences, keep the open time flexible around the confirmed timings.",
            "The time between the included experiences is left flexible for a meal, a rest or your own plans.",
            "Any open time today sits between arranged experiences, so it is best kept flexible around the schedule.",
        ), facts, intent)

    if schedule.has_multiple_arranged_activities:
        return choose_copy_variant((
            "After the included experiences, the rest of the day is open for your own plans.",
            "Once today’s arranged experiences are complete, the remaining schedule is left flexible for you.",
            "The included experiences anchor the day, with any extra time kept flexible around your own plans.",
        ), facts, intent)

    if intent == DayIntent.ACTIVITY_DAY or (facts.has_activity and not facts.has_travel):
        return choose_copy_variant((
            "After the included experience, the rest of the day is open for your own plans.",
            "Once the included experience is complete, the rest of the day is left open for your own plans.",
            "The included experience anchors the day, with the remaining schedule left flexible for you.",
        ), facts, intent)

    if intent == DayIntent.ACTIVITY_PLUS_TRAVEL or (facts.has_activity and facts.has_travel):
        if schedule.has_evening_activity and facts.travel_heavy:
            return "Any open time today is limited and should stay flexible between the travel arrangements and the evening experience."
        return choose_copy_variant((
            "After the included arrangements, any free time can be kept flexible around the day’s timing.",
            "Any open time today should stay flexible around the included arrangements and travel timing.",
            "The day combines arranged experiences with logistics, so open time is best kept flexible.",
        ), facts, intent)

    if intent == DayIntent.ARRIVAL_STAY or facts.has_arrival:
        return choose_copy_variant((
            "After arrival, any remaining time is best kept simple, with space to settle in and get oriented.",
            "After arrival, keep any open time simple, with space to settle in and get oriented.",
            "Once you have arrived, the rest of the day can stay light and flexible around settling in.",
        ), facts, intent)

    if intent == DayIntent.SAME_CITY_ACCOMMODATION_CHANGE:
        return "Outside the move between stays, the day can remain flexible around the listed arrangements."

    if intent == DayIntent.RETURN_VISIT:
        return "Once back in the area, any open time can be used flexibly around the listed arrangements."

    if city and city != "the area":
        return choose_copy_variant((
            f"Any open time in {city} is left flexible for your own plans.",
            f"Open time in {city} is kept flexible for your own pace and plans.",
            f"The schedule leaves any extra time in {city} open for independent plans.",
        ), facts, intent)
    return choose_copy_variant((
        "Any open time today is left flexible for your own plans.",
        "Any extra time today remains open for your own pace and plans.",
        "The schedule leaves open time flexible around your own plans.",
    ), facts, intent)


def create_leisure_copy(
    rows: Sequence[Mapping[str, Any]] | None,
    *,
    visit_context: object | None = None,
    facts: DayFacts | None = None,
    intent: DayIntent | None = None,
) -> str:
    """Convenience wrapper used by renderers that only have source rows."""

    facts = facts or build_day_facts(rows, visit_context=visit_context)
    intent = intent or classify_day_intent(facts)
    return write_leisure_copy(facts, intent)


__all__ = ["create_leisure_copy", "write_leisure_copy"]

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
        return "Keep any spare time practical today, with room for transfers, check-in and the arranged schedule."

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
            "The time between today’s included experiences is best used lightly — for a meal, a rest, or a short independent stroll close by.",
            "Between the arranged experiences, keep things easy with time for a meal, a quiet pause, or a small local discovery.",
            "The gap between the included experiences stays flexible, giving you space to pause without overfilling the day.",
        ), facts, intent)

    if schedule.has_multiple_arranged_activities:
        return choose_copy_variant((
            "Once today’s arranged experiences are complete, use any extra time for a relaxed meal, a short walk, or a quiet pause back at the hotel.",
            "The included experiences anchor the day, while any spare time can stay simple and close to the day’s route.",
            "After the arranged experiences, keep the remaining time easy rather than adding too much to the schedule.",
        ), facts, intent)

    if intent == DayIntent.ACTIVITY_DAY or (facts.has_activity and not facts.has_travel):
        return choose_copy_variant((
            "After the included experience, use the rest of the day for a relaxed meal, a local stroll, or anything you would rather discover independently.",
            "Once the included experience is complete, the schedule stays light so you can follow your own pace for the rest of the day.",
            "The included experience anchors the day, leaving the remaining time easy and flexible around your own interests.",
        ), facts, intent)

    if intent == DayIntent.ACTIVITY_PLUS_TRAVEL or (facts.has_activity and facts.has_travel):
        if schedule.has_evening_activity and facts.travel_heavy:
            return "Any open time today is limited and should stay flexible between the travel arrangements and the evening experience."
        return choose_copy_variant((
            "With both logistics and included arrangements today, keep any spare time light and close to the confirmed schedule.",
            "Any open time should stay practical today, giving you room around transfers, check-in and the included arrangements.",
            "The day combines travel with arranged experiences, so it is best not to overfill the unscheduled moments.",
        ), facts, intent)

    if intent == DayIntent.ARRIVAL_STAY or facts.has_arrival:
        return choose_copy_variant((
            "Once settled, this is a good moment for an easy local walk, a first meal nearby, or simply easing into the trip.",
            "After arrival, keep the day gentle with time to unpack, rest, and find your bearings close to the hotel.",
            "Use the arrival day lightly, leaving space to settle in before the trip becomes more active.",
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

"""Context-aware leisure/free-time copy writer."""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from itinerary_generation.copy_decision_contract import CopyDecisionTrace, decision_candidate, finalize_decision
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


def _trace(text: str, *, source: str, reason: str, facts: DayFacts, intent: DayIntent, priority: int = 80) -> CopyDecisionTrace:
    selected = decision_candidate(text, source=source, priority=priority, reason=reason)
    assert selected is not None
    return finalize_decision(
        kind="leisure_copy",
        selected=selected,
        context={
            "intent": getattr(intent, "name", str(intent)),
            "city": _fallback_city(facts),
            "schedule_shape": getattr(facts.schedule_profile, "shape", ""),
        },
    )


def _primary_context_decision(facts: DayFacts, intent: DayIntent, city: str) -> CopyDecisionTrace | None:
    if intent == DayIntent.CRUISE_DAY or facts.cruise_onboard_day:
        text = _sentence(choose_copy_variant((
            "Time onboard is open for you to enjoy the sailing, the ship facilities and the coastal views as the route continues.",
            "Your time onboard remains flexible, with space to enjoy the ship facilities and the changing coastal views.",
            "Onboard time is left open for the sailing itself, the ship facilities and the views along the route.",
        ), facts, intent))
        return _trace(text, source="cruise_onboard_leisure", reason="Cruise/onboard facts own free-time wording for sailing days.", facts=facts, intent=intent)

    if facts.travel_heavy or intent in {DayIntent.TRAVEL_DAY, DayIntent.OVERNIGHT_TRANSPORT_DAY, DayIntent.ARRIVAL_ONWARD_TRAVEL}:
        return _trace(
            "Keep any spare time practical today, with room for transfers, check-in and the arranged schedule.",
            source="travel_heavy_leisure",
            reason="Travel-heavy days should not suggest broad sightseeing/free-time promises.",
            facts=facts,
            intent=intent,
        )

    if intent == DayIntent.FULL_LEISURE_DAY or facts.full_leisure_day:
        text = (
            f"Today is open for independent time in {city}. You may explore locally, keep the pace relaxed, or simply enjoy a quieter day between arranged experiences."
            if city and city != "the area"
            else "Today is open for independent time, with space to rest, explore locally or keep the pace flexible."
        )
        return _trace(_sentence(text), source="full_leisure_day", reason="Full-leisure intent owns this copy.", facts=facts, intent=intent)
    return None


def _schedule_decision(facts: DayFacts, intent: DayIntent) -> CopyDecisionTrace | None:
    schedule = facts.schedule_profile
    if schedule.has_multiple_arranged_activities and (
        schedule.has_leisure_between_activities
        or schedule.has_activity_after_leisure
        or schedule.has_gap_between_activities
    ):
        text = choose_copy_variant((
            "The time between today’s included experiences is best used lightly — for a meal, a rest, or a short independent stroll close by.",
            "Between the arranged experiences, keep things easy with time for a meal, a quiet pause, or a small local discovery.",
            "The gap between the included experiences stays flexible, giving you space to pause without overfilling the day.",
        ), facts, intent)
        return _trace(text, source="between_arranged_experiences", reason="Schedule Brain found a real gap between arranged experiences.", facts=facts, intent=intent)

    occupancy = schedule.occupancy
    if occupancy.has_invalid_time_range:
        return _trace(
            "Keep any unscheduled time flexible until the confirmed activity timing has been checked.",
            source="invalid_schedule_time",
            reason="Schedule Brain found an invalid or reversed supplier time range, so no free-time window is claimed.",
            facts=facts,
            intent=intent,
        )
    if occupancy.is_full_day and occupancy.finishes_late:
        return _trace(
            "The arranged experience fills the day into the evening, so no additional plans are suggested.",
            source="full_day_late_schedule",
            reason="Schedule occupancy shows a full-day experience with a late finish.",
            facts=facts,
            intent=intent,
        )
    if occupancy.is_full_day:
        return _trace(
            "The included experience occupies most of the day, leaving only practical time around meals and rest.",
            source="full_day_schedule",
            reason="Schedule occupancy shows at least eight arranged hours or a nine-hour activity span.",
            facts=facts,
            intent=intent,
        )
    if not occupancy.has_meaningful_post_activity_time and occupancy.last_end_minutes is not None:
        return _trace(
            "The experience finishes late, so keep the remaining time practical around dinner and rest.",
            source="late_finish_schedule",
            reason="Schedule occupancy does not support a meaningful post-activity leisure window.",
            facts=facts,
            intent=intent,
        )
    return None


def _activity_and_arrival_decision(facts: DayFacts, intent: DayIntent) -> CopyDecisionTrace | None:
    schedule = facts.schedule_profile
    if schedule.has_multiple_arranged_activities:
        text = choose_copy_variant((
            "Once today’s arranged experiences are complete, use any extra time for a relaxed meal, a short walk, or a quiet pause back at the hotel.",
            "The included experiences anchor the day, while any spare time can stay simple and close to the day’s route.",
            "After the arranged experiences, keep the remaining time easy rather than adding too much to the schedule.",
        ), facts, intent)
        return _trace(text, source="multi_activity_leisure", reason="Multiple arranged activities limit how strongly free time should be promoted.", facts=facts, intent=intent)

    if intent == DayIntent.ACTIVITY_DAY or (facts.has_activity and not facts.has_travel):
        text = choose_copy_variant((
            "After the included experience, use the rest of the day for a relaxed meal, a local stroll, or anything you would rather discover independently.",
            "Once the included experience is complete, the schedule stays light so you can follow your own pace for the rest of the day.",
            "The included experience anchors the day, leaving the remaining time easy and flexible around your own interests.",
        ), facts, intent)
        return _trace(text, source="activity_day_leisure", reason="A single arranged activity leaves controlled independent time afterward.", facts=facts, intent=intent)

    if intent == DayIntent.ACTIVITY_PLUS_TRAVEL or (facts.has_activity and facts.has_travel):
        if schedule.has_evening_activity and facts.travel_heavy:
            text = "Any open time today is limited and should stay flexible between the travel arrangements and the evening experience."
        else:
            text = choose_copy_variant((
                "With both logistics and included arrangements today, keep any spare time light and close to the confirmed schedule.",
                "Any open time should stay practical today, giving you room around transfers, check-in and the included arrangements.",
                "The day combines travel with arranged experiences, so it is best not to overfill the unscheduled moments.",
            ), facts, intent)
        return _trace(text, source="activity_plus_travel_leisure", reason="Travel plus activities requires practical free-time wording.", facts=facts, intent=intent)

    if intent == DayIntent.ARRIVAL_STAY or facts.has_arrival:
        text = choose_copy_variant((
            "Once settled, this is a good moment for an easy local walk, a first meal nearby, or simply easing into the trip.",
            "After arrival, keep the day gentle with time to unpack, rest, and find your bearings close to the hotel.",
            "Use the arrival day lightly, leaving space to settle in before the trip becomes more active.",
        ), facts, intent)
        return _trace(text, source="arrival_day_leisure", reason="Arrival-day leisure should stay gentle and practical.", facts=facts, intent=intent)
    return None


def _fallback_decision(facts: DayFacts, intent: DayIntent, city: str) -> CopyDecisionTrace:
    if intent == DayIntent.SAME_CITY_ACCOMMODATION_CHANGE:
        return _trace(
            "Outside the move between stays, the day can remain flexible around the listed arrangements.",
            source="accommodation_change_leisure",
            reason="Same-city stay changes keep free time around the move.",
            facts=facts,
            intent=intent,
        )
    if intent == DayIntent.RETURN_VISIT:
        return _trace(
            "Once back in the area, any open time can be used flexibly around the listed arrangements.",
            source="return_visit_leisure",
            reason="Return-visit context owns this leisure wording.",
            facts=facts,
            intent=intent,
        )
    if city and city != "the area":
        text = choose_copy_variant((
            f"Any open time in {city} is left flexible for your own plans.",
            f"Open time in {city} is kept flexible for your own pace and plans.",
            f"The schedule leaves any extra time in {city} open for independent plans.",
        ), facts, intent)
        return _trace(text, source="city_open_time_fallback", reason="No stronger leisure context was available, so city open-time fallback was used.", facts=facts, intent=intent, priority=40)
    text = choose_copy_variant((
        "Any open time today is left flexible for your own plans.",
        "Any extra time today remains open for your own pace and plans.",
        "The schedule leaves open time flexible around your own plans.",
    ), facts, intent)
    return _trace(text, source="open_time_fallback", reason="No stronger leisure context was available.", facts=facts, intent=intent, priority=35)


def plan_leisure_decision(facts: DayFacts, intent: DayIntent | None = None) -> CopyDecisionTrace:
    """Return free-time copy with traceable context/source metadata."""

    intent = intent or classify_day_intent(facts)
    city = _fallback_city(facts)
    for decision in (
        _primary_context_decision(facts, intent, city),
        _schedule_decision(facts, intent),
        _activity_and_arrival_decision(facts, intent),
    ):
        if decision is not None:
            return decision
    return _fallback_decision(facts, intent, city)


def write_leisure_copy(facts: DayFacts, intent: DayIntent | None = None) -> str:
    """Return free-time copy from day facts and intent."""

    return plan_leisure_decision(facts, intent).text


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


__all__ = ["create_leisure_copy", "plan_leisure_decision", "write_leisure_copy"]

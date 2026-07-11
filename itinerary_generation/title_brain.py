"""Title Brain for day headings.

Chooses a day title that represents the whole day, not just the first or most
exciting row. The public writer still returns a string, but the actual decision
is produced as a traceable contract so title bugs can be tested at the source
priority level instead of patched one symptom at a time.
"""

from __future__ import annotations

import re
from typing import Mapping, Sequence

from itinerary_generation.common import TRANSPORT_TYPES, get_primary_city, get_row_type, has_hotel
from itinerary_generation.copy_decision_contract import CopyDecisionCandidate, CopyDecisionTrace, finalize_decision
from itinerary_generation.day_facts import DayFacts, build_day_facts
from itinerary_generation.day_intent import DayIntent, classify_day_intent
from itinerary_generation.day_leisure_facts import is_blank_activity_or_leisure
from itinerary_generation.schedule_brain import DayScheduleProfile, build_day_schedule_profile
from itinerary_generation.title_decision_contract import compose_activity_day_title, select_activity_title
from itinerary_generation.title_decision_helpers import (
    clean_title_value,
    join_day_titles,
    shorten_day_title,
    title_trace,
    transport_title_candidate,
)
from itinerary_generation.title_intent_decisions import arrival_or_return_title, departure_or_stay_change_title
from itinerary_generation.title_travel_composition import compose_activity_overnight_transport_title
from itinerary_generation.transport import get_primary_transport_title
from itinerary_generation.transport_domain.route_summary import transport_destination_from_row
from text_polish import polish_title

TRAVEL_ROW_TYPES = set(TRANSPORT_TYPES) | {"Transfer", "Transport", "Coach", "Bus", "Drive"}


def _city(rows: Sequence[Mapping[str, object]], facts: DayFacts) -> str:
    return polish_title(facts.main_city or facts.end_city or get_primary_city([dict(row) for row in rows]) or "")


def _activity_rows(rows: Sequence[Mapping[str, object]]) -> list[dict]:
    result: list[dict] = []
    for row in rows or []:
        if get_row_type(dict(row)) != "Activity":
            continue
        if is_blank_activity_or_leisure(row):
            continue
        result.append(dict(row))
    return result


def _route_destination(rows: Sequence[Mapping[str, object]], facts: DayFacts) -> str:
    for row in rows or []:
        if get_row_type(dict(row)) in {"Train", "Flight", "Cruise", "Ferry", "Transport", "Coach", "Bus", "Drive"}:
            destination = transport_destination_from_row(dict(row))
            if destination:
                return polish_title(destination)
    return polish_title(facts.route_destination or facts.end_city or facts.main_city)


def _travel_title_decision(rows: Sequence[Mapping[str, object]], facts: DayFacts, city: str) -> CopyDecisionTrace:
    primary = get_primary_transport_title([dict(row) for row in rows])
    primary_candidate = transport_title_candidate(primary) if primary else None
    if primary_candidate:
        return finalize_decision(kind="day_title", selected=primary_candidate, candidates=(primary_candidate,), context={"intent": "travel"})
    destination = _route_destination(rows, facts) or city
    return title_trace(
        f"Travel to {destination}" if destination else "Travel day",
        source="travel_intent_title",
        priority=76,
        reason="No primary transport title was available, so the day title comes from the route destination.",
        candidates=(primary_candidate,),
    )


def _arrival_activity_title_decision(city: str, activity_trace: CopyDecisionTrace, facts: DayFacts, schedule: DayScheduleProfile) -> CopyDecisionTrace:
    activity_title = activity_trace.text
    if not activity_title:
        return title_trace(
            f"Arrival in {city}" if city else "Arrival",
            source="arrival_intent_title",
            priority=74,
            reason="Arrival day has no arranged activity title to combine.",
            candidates=activity_trace.candidates,
        )
    if city and city.casefold() == "longyearbyen" and facts.has_flight:
        return title_trace(
            f"Journey to Svalbard and {activity_title}",
            source="arrival_activity_composed_title",
            priority=94,
            reason="Flight arrival into Longyearbyen should be titled as the Svalbard journey plus activity.",
            candidates=activity_trace.candidates,
        )
    if len(activity_title) > 45 and "cruise" not in activity_title.lower():
        return title_trace(
            shorten_day_title(activity_title),
            source="activity_title_length_guard",
            priority=88,
            reason="Broad activity title is too long for the day heading and was safely shortened.",
            candidates=activity_trace.candidates,
        )
    if city and (facts.has_route_transport or schedule.has_evening_activity):
        return title_trace(
            join_day_titles(f"Arrival in {city}", activity_title),
            source="arrival_activity_composed_title",
            priority=94,
            reason="The day combines arrival/travel context with a real arranged activity.",
            candidates=activity_trace.candidates,
        )
    return finalize_decision(kind="day_title", selected=activity_trace.selected, candidates=activity_trace.candidates, context={"intent": "activity_plus_travel"})


def _activity_title_for_day(
    *,
    activities: Sequence[Mapping[str, object]],
    activity_decision: CopyDecisionTrace | None,
    facts: DayFacts,
    intent: DayIntent,
    schedule: DayScheduleProfile,
    city: str,
    primary_transport_title: str,
    context: Mapping[str, str],
) -> CopyDecisionTrace | None:
    if activities and schedule.has_multiple_arranged_activities:
        if schedule.first_activity_title and schedule.last_activity_title:
            title = join_day_titles(schedule.first_activity_title, schedule.last_activity_title)
            if title:
                return title_trace(
                    title,
                    source="schedule_composed_activity_title",
                    priority=92,
                    reason="Schedule Brain identified the first and last arranged activities for a whole-day title.",
                    candidates=activity_decision.candidates if activity_decision else (),
                    context=context,
                )
        if activity_decision and activity_decision.text:
            return finalize_decision(kind="day_title", selected=activity_decision.selected, candidates=activity_decision.candidates, context=context)

    if activities and intent == DayIntent.ACTIVITY_PLUS_TRAVEL:
        activity_trace = select_activity_title(activities[0])
        overnight_title = compose_activity_overnight_transport_title(
            activity_trace=activity_trace,
            transport_title=primary_transport_title,
            facts=facts,
        )
        return overnight_title or _arrival_activity_title_decision(city, activity_trace, facts, schedule)

    if activities and activity_decision:
        return finalize_decision(kind="day_title", selected=activity_decision.selected, candidates=activity_decision.candidates, context=context)
    return None


def _transport_or_fallback_title(
    *,
    row_list: Sequence[Mapping[str, object]],
    facts: DayFacts,
    intent: DayIntent,
    city: str,
    activities: Sequence[Mapping[str, object]],
    primary_transport_candidate: CopyDecisionCandidate | None,
    context: Mapping[str, str],
) -> CopyDecisionTrace:
    if facts.has_route_transport and not activities:
        transport_from_activity = any(
            str(row.get("source_type") or row.get("type") or "").casefold() == "activity"
            and get_row_type(dict(row)) in TRAVEL_ROW_TYPES
            for row in row_list
        )
        if primary_transport_candidate and (
            transport_from_activity
            or facts.has_train
            or facts.has_flight
            or facts.has_ferry
            or facts.has_cruise
            or facts.has_self_drive
            or re.search(r"\bcoach\b", primary_transport_candidate.text, flags=re.IGNORECASE)
        ):
            return finalize_decision(kind="day_title", selected=primary_transport_candidate, candidates=(primary_transport_candidate,), context=context)
        if intent == DayIntent.ARRIVAL_STAY and city:
            return title_trace(
                f"Arrival in {city}",
                source="arrival_intent_title",
                priority=78,
                reason="Arrival-stay intent owns this title when transport is only local logistics.",
                candidates=(primary_transport_candidate,),
                context=context,
            )
        return _travel_title_decision(row_list, facts, city)
    if intent == DayIntent.FULL_LEISURE_DAY:
        return title_trace(f"A day at leisure in {city}" if city else "A day at leisure", source="leisure_intent_title", priority=72, reason="Full-leisure-day intent owns this title.", context=context)
    if has_hotel(row_list) and city:
        return title_trace(f"Welcome to {city}", source="stay_title_fallback", priority=60, reason="Hotel stay without a stronger day pattern falls back to destination welcome.", risk_flags=("fallback_title",), context=context)
    return title_trace(f"Day in {city}" if city else "Day at leisure", source="last_resort_title_fallback", priority=10, reason="No stronger day-title source was available.", risk_flags=("fallback_title",), context=context)


def plan_day_title_decision(
    rows: Sequence[Mapping[str, object]] | None,
    *,
    visit_context: object | None = None,
    facts: DayFacts | None = None,
    intent: DayIntent | None = None,
    schedule: DayScheduleProfile | None = None,
) -> CopyDecisionTrace:
    """Return a traceable day-title decision."""

    row_list = [dict(row) for row in (rows or []) if isinstance(row, Mapping)]
    facts = facts or build_day_facts(row_list, visit_context=visit_context)
    intent = intent or classify_day_intent(facts)
    schedule = schedule or build_day_schedule_profile(row_list)
    city = _city(row_list, facts)
    activities = _activity_rows(row_list)
    activity_decision = compose_activity_day_title(activities) if activities else None
    primary_transport_title = get_primary_transport_title(row_list)
    primary_transport_candidate = transport_title_candidate(primary_transport_title) if primary_transport_title else None
    raw_day_text = " ".join(str(row.get(key) or "") for row in row_list for key in ("title", "original_title", "details")).lower()
    context = {"intent": getattr(intent, "name", str(intent)), "city": city}

    if "excursion to tallinn" in raw_day_text:
        return title_trace(
            "Day Excursion to Tallinn",
            source="known_day_product_title",
            priority=95,
            reason="Tallinn day excursion is a known whole-day product pattern.",
            candidates=activity_decision.candidates if activity_decision else (),
            context=context,
        )

    decision = departure_or_stay_change_title(
        row_list=row_list,
        facts=facts,
        intent=intent,
        city=city,
        raw_day_text=raw_day_text,
        primary_transport_candidate=primary_transport_candidate,
        context=context,
    )
    if decision is not None:
        return decision

    decision = arrival_or_return_title(
        facts=facts,
        intent=intent,
        city=city,
        activities=activities,
        primary_transport_candidate=primary_transport_candidate,
        context=context,
    )
    if decision is not None:
        return decision

    decision = _activity_title_for_day(
        activities=activities,
        activity_decision=activity_decision,
        facts=facts,
        intent=intent,
        schedule=schedule,
        city=city,
        primary_transport_title=primary_transport_title,
        context=context,
    )
    if decision is not None:
        return decision

    return _transport_or_fallback_title(
        row_list=row_list,
        facts=facts,
        intent=intent,
        city=city,
        activities=activities,
        primary_transport_candidate=primary_transport_candidate,
        context=context,
    )

def write_day_title(
    rows: Sequence[Mapping[str, object]] | None,
    *,
    visit_context: object | None = None,
    facts: DayFacts | None = None,
    intent: DayIntent | None = None,
    schedule: DayScheduleProfile | None = None,
) -> str:
    """Return a whole-day title from sub-brain facts."""

    return plan_day_title_decision(
        rows,
        visit_context=visit_context,
        facts=facts,
        intent=intent,
        schedule=schedule,
    ).text


__all__ = ["plan_day_title_decision", "write_day_title"]

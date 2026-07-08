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
from itinerary_generation.copy_decision_contract import CopyDecisionCandidate, CopyDecisionTrace, decision_candidate, finalize_decision
from itinerary_generation.day_facts import DayFacts, build_day_facts
from itinerary_generation.day_intent import DayIntent, classify_day_intent
from itinerary_generation.schedule_brain import DayScheduleProfile, build_day_schedule_profile
from itinerary_generation.title_decision_contract import compose_activity_day_title, join_title_text, select_activity_title
from itinerary_generation.transport import get_primary_transport_title
from itinerary_generation.transport_domain.route_summary import transport_destination_from_row
from place_aliases import country_for_place
from text_polish import polish_title

TRAVEL_ROW_TYPES = set(TRANSPORT_TYPES) | {"Transfer", "Transport", "Coach", "Bus"}


def _clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _city(rows: Sequence[Mapping[str, object]], facts: DayFacts) -> str:
    return polish_title(facts.main_city or facts.end_city or get_primary_city([dict(row) for row in rows]) or "")


def _activity_rows(rows: Sequence[Mapping[str, object]]) -> list[dict]:
    result: list[dict] = []
    for row in rows or []:
        if get_row_type(dict(row)) != "Activity":
            continue
        text = _clean(" ".join(str(row.get(key) or "") for key in ("title", "original_title", "details"))).lower()
        if "spend time at leisure" in text or text.strip() in {"leisure", "free time"}:
            continue
        result.append(dict(row))
    return result


def _single_activity_title(row: Mapping[str, object]) -> str:
    return select_activity_title(row).text


def _multi_activity_title(activity_rows: Sequence[Mapping[str, object]]) -> str:
    return compose_activity_day_title(activity_rows).text


def _route_destination(rows: Sequence[Mapping[str, object]], facts: DayFacts) -> str:
    for row in rows or []:
        if get_row_type(dict(row)) in {"Train", "Flight", "Cruise", "Ferry", "Transport", "Coach", "Bus"}:
            destination = transport_destination_from_row(dict(row))
            if destination:
                return polish_title(destination)
    return polish_title(facts.route_destination or facts.end_city or facts.main_city)


def _short_title(value: str) -> str:
    text = _clean(value).strip(" -:|.,")
    lower = text.lower()
    if "walrus" in lower and "safari" in lower:
        return "Walrus Safari"
    if "reindeer" in lower and "sámi" in lower:
        return "Reindeer & Sámi Culture"
    if "northern lights" in lower and "hunt" in lower:
        return "Northern Lights Hunt"
    if "northern lights" in lower and "chase" in lower:
        return "Northern Lights Chase"
    if "northern lights" in lower and "cruise" in lower:
        return "Northern Lights Cruise"
    if "walking tour" in lower and "bergen" in lower:
        return "Bergen Walking Tour"
    return text


def _join_titles(first: str, second: str, *, max_length: int = 82) -> str:
    title = join_title_text(first, second, max_length=max_length)
    if len(title) <= max_length:
        return title
    short_title = join_title_text(_short_title(first), _short_title(second), max_length=max_length)
    return short_title if len(short_title) <= max_length else first


def _transport_candidate(text: str, *, source: str = "transport_title", priority: int = 84) -> CopyDecisionCandidate | None:
    return decision_candidate(
        polish_title(text),
        source=source,
        priority=priority,
        reason="Transport domain provided the primary route title for this day.",
    )


def _intent_candidate(text: str, *, source: str, reason: str, priority: int = 78, risk_flags: tuple[str, ...] = ()) -> CopyDecisionCandidate:
    candidate = decision_candidate(text, source=source, priority=priority, reason=reason, risk_flags=risk_flags)
    assert candidate is not None
    return candidate


def _trace(
    text: str,
    *,
    source: str,
    reason: str,
    candidates: Sequence[CopyDecisionCandidate | None] = (),
    priority: int = 90,
    risk_flags: tuple[str, ...] = (),
    context: Mapping[str, str] | None = None,
) -> CopyDecisionTrace:
    selected = decision_candidate(text, source=source, priority=priority, reason=reason, risk_flags=risk_flags)
    assert selected is not None
    return finalize_decision(kind="day_title", selected=selected, candidates=candidates, context=context)


def _travel_title_decision(rows: Sequence[Mapping[str, object]], facts: DayFacts, city: str) -> CopyDecisionTrace:
    primary = get_primary_transport_title([dict(row) for row in rows])
    primary_candidate = _transport_candidate(primary) if primary else None
    if primary_candidate:
        return finalize_decision(kind="day_title", selected=primary_candidate, candidates=(primary_candidate,), context={"intent": "travel"})
    destination = _route_destination(rows, facts) or city
    return _trace(
        f"Travel to {destination}" if destination else "Travel day",
        source="travel_intent_title",
        priority=76,
        reason="No primary transport title was available, so the day title comes from the route destination.",
        candidates=(primary_candidate,),
    )


def _arrival_activity_title_decision(city: str, activity_trace: CopyDecisionTrace, facts: DayFacts, schedule: DayScheduleProfile) -> CopyDecisionTrace:
    activity_title = activity_trace.text
    if not activity_title:
        return _trace(
            f"Arrival in {city}" if city else "Arrival",
            source="arrival_intent_title",
            priority=74,
            reason="Arrival day has no arranged activity title to combine.",
            candidates=activity_trace.candidates,
        )
    if city and city.casefold() == "longyearbyen" and facts.has_flight:
        return _trace(
            f"Journey to Svalbard and {activity_title}",
            source="arrival_activity_composed_title",
            priority=94,
            reason="Flight arrival into Longyearbyen should be titled as the Svalbard journey plus activity.",
            candidates=activity_trace.candidates,
        )
    if len(activity_title) > 45 and "cruise" not in activity_title.lower():
        return _trace(
            _short_title(activity_title),
            source="activity_title_length_guard",
            priority=88,
            reason="Broad activity title is too long for the day heading and was safely shortened.",
            candidates=activity_trace.candidates,
        )
    if city and (facts.has_route_transport or schedule.has_evening_activity):
        return _trace(
            _join_titles(f"Arrival in {city}", activity_title),
            source="arrival_activity_composed_title",
            priority=94,
            reason="The day combines arrival/travel context with a real arranged activity.",
            candidates=activity_trace.candidates,
        )
    return finalize_decision(kind="day_title", selected=activity_trace.selected, candidates=activity_trace.candidates, context={"intent": "activity_plus_travel"})


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
    primary_transport_candidate = _transport_candidate(primary_transport_title) if primary_transport_title else None
    raw_day_text = " ".join(
        str(row.get(key) or "")
        for row in row_list
        for key in ("title", "original_title", "details")
    ).lower()
    context = {"intent": getattr(intent, "name", str(intent)), "city": city}

    if "excursion to tallinn" in raw_day_text:
        return _trace(
            "Day Excursion to Tallinn",
            source="known_day_product_title",
            priority=95,
            reason="Tallinn day excursion is a known whole-day product pattern.",
            candidates=activity_decision.candidates if activity_decision else (),
            context=context,
        )

    if intent == DayIntent.DEPARTURE_DAY:
        return _trace(f"Departure from {city}" if city else "Departure", source="departure_intent_title", priority=78, reason="Departure-day intent owns the day title.", context=context)

    if intent == DayIntent.SAME_CITY_ACCOMMODATION_CHANGE:
        hotel_titles = [
            _clean(row.get("title") or row.get("hotel_name") or row.get("original_title"))
            for row in row_list
            if get_row_type(dict(row)) == "Hotel"
        ]
        hotel_text = " ".join(
            _clean(row.get(key))
            for row in row_list
            if get_row_type(dict(row)) == "Hotel"
            for key in ("title", "hotel_name", "original_title", "room_category", "details")
        ).lower()
        for hotel_title in hotel_titles:
            if "snow hotel" in hotel_title.lower() or "snowhotel" in hotel_title.lower():
                title = "Arctic Snow Hotel Stay" if "arctic" in hotel_title.lower() else f"{polish_title(hotel_title)} Stay"
                return _trace(title, source="distinctive_accommodation_title", priority=90, reason="Distinctive accommodation owns this same-city move title.", context=context)
        if "glass igloo" in hotel_text or "igloo" in hotel_text:
            return _trace(f"Glass Igloo Stay in {city}" if city else "Glass Igloo Stay", source="distinctive_accommodation_title", priority=90, reason="Distinctive glass-igloo stay owns this day title.", context=context)
        if facts.return_visit and "next accommodation" not in raw_day_text:
            return _trace(f"Return to {city}" if city else "Return Visit", source="return_visit_title", priority=80, reason="Visit context marks this as a return stay.", context=context)
        return _trace(f"Next Stay in {city}" if city else "Next Stay", source="accommodation_change_title", priority=76, reason="Same-city accommodation change owns this day title.", context=context)

    if intent == DayIntent.ARRIVAL_ONWARD_TRAVEL:
        destination = polish_title(facts.onward_destination or facts.end_city or "")
        return _trace(f"Arrival and travel to {destination}" if destination else "Arrival and travel day", source="arrival_onward_title", priority=82, reason="Arrival plus onward-travel intent owns this day title.", candidates=(primary_transport_candidate,), context=context)

    if facts.has_route_transport and not activities and primary_transport_candidate and (facts.has_train or facts.has_flight or facts.has_ferry or facts.has_cruise):
        return finalize_decision(kind="day_title", selected=primary_transport_candidate, candidates=(primary_transport_candidate,), context=context)

    if intent == DayIntent.RETURN_VISIT:
        return _trace(f"Return to {city}" if city else "Return Visit", source="return_visit_title", priority=80, reason="Visit context marks this as a return stay.", context=context)

    if activities and schedule.has_multiple_arranged_activities:
        if schedule.first_activity_title and schedule.last_activity_title:
            title = _join_titles(schedule.first_activity_title, schedule.last_activity_title)
            if title:
                return _trace(title, source="schedule_composed_activity_title", priority=92, reason="Schedule Brain identified the first and last arranged activities for a whole-day title.", candidates=activity_decision.candidates if activity_decision else (), context=context)
        if activity_decision and activity_decision.text:
            return finalize_decision(kind="day_title", selected=activity_decision.selected, candidates=activity_decision.candidates, context=context)

    if activities and intent == DayIntent.ACTIVITY_PLUS_TRAVEL:
        activity_trace = select_activity_title(activities[0])
        return _arrival_activity_title_decision(city, activity_trace, facts, schedule)

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
            or re.search(r"\bcoach\b", primary_transport_candidate.text, flags=re.IGNORECASE)
        ):
            return finalize_decision(kind="day_title", selected=primary_transport_candidate, candidates=(primary_transport_candidate,), context=context)
        if intent == DayIntent.ARRIVAL_STAY and city:
            return _trace(f"Arrival in {city}", source="arrival_intent_title", priority=78, reason="Arrival-stay intent owns this title when transport is only local logistics.", candidates=(primary_transport_candidate,), context=context)
        return _travel_title_decision(row_list, facts, city)

    if intent == DayIntent.ARRIVAL_STAY and city:
        if facts.return_visit:
            return _trace(f"Return to {city}", source="return_visit_title", priority=80, reason="Visit context marks this as a return stay.", context=context)
        if country_for_place(city) == "Iceland":
            return _trace("Welcome to Iceland", source="arrival_country_title", priority=78, reason="Iceland arrival title uses country-level welcome wording.", context=context)
        return _trace(f"Welcome to {city}", source="arrival_intent_title", priority=78, reason="Arrival-stay intent owns this day title.", context=context)

    if activities and activity_decision:
        return finalize_decision(kind="day_title", selected=activity_decision.selected, candidates=activity_decision.candidates, context=context)

    if intent == DayIntent.FULL_LEISURE_DAY:
        return _trace(f"A day at leisure in {city}" if city else "A day at leisure", source="leisure_intent_title", priority=72, reason="Full-leisure-day intent owns this title.", context=context)

    if has_hotel(row_list) and city:
        return _trace(f"Welcome to {city}", source="stay_title_fallback", priority=60, reason="Hotel stay without a stronger day pattern falls back to destination welcome.", risk_flags=("fallback_title",), context=context)

    return _trace(f"Day in {city}" if city else "Day at leisure", source="last_resort_title_fallback", priority=10, reason="No stronger day-title source was available.", risk_flags=("fallback_title",), context=context)


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

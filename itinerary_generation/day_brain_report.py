"""Developer-facing Day Brain inspection reports."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Iterable, Mapping, Sequence

from itinerary_generation.copy.visit_context import DayVisitContext, build_day_visit_contexts
from itinerary_generation.day_copy_qa import find_day_copy_issues
from itinerary_generation.day_facts import DayFacts, build_day_facts
from itinerary_generation.day_intent import DayIntent, classify_day_intent
from itinerary_generation.day_leisure_writer import write_leisure_copy
from itinerary_generation.day_text import create_day_intro
from itinerary_generation.day_timeline_events import TimelineEvent, summarize_timeline_events


def _clean(value: object) -> str:
    return str(value or "").strip()


def _dataclass_payload(value: object) -> dict[str, Any]:
    if is_dataclass(value):
        payload = asdict(value)
        return {key: _json_safe(item) for key, item in payload.items()}
    return {}


def _json_safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if is_dataclass(value):
        return _dataclass_payload(value)
    return str(value)


def timeline_event_payload(event: TimelineEvent) -> dict[str, Any]:
    """Return a compact JSON-safe payload for one normalized event."""

    return {
        "order": event.order,
        "row_type": event.row_type,
        "kind": event.kind,
        "city": event.city,
        "origin": event.origin,
        "destination": event.destination,
        "mode": event.mode,
        "target_kind": event.target_kind,
        "is_route": event.is_route,
        "is_local": event.is_local,
        "is_overnight": event.is_overnight,
        "is_leisure": event.is_leisure,
        "flags": sorted(event.flags),
        "source_row_id": event.source_row_id,
    }


def day_facts_payload(facts: DayFacts) -> dict[str, Any]:
    """Return the fact fields most useful when reviewing generated copy."""

    return {
        "row_types": list(facts.row_types),
        "city_sequence": list(facts.city_sequence),
        "route_origins": list(facts.route_origins),
        "route_destinations": list(facts.route_destinations),
        "hotel_cities": list(facts.hotel_cities),
        "activity_cities": list(facts.activity_cities),
        "start_city": facts.start_city,
        "end_city": facts.end_city,
        "main_city": facts.main_city,
        "arrival_city": facts.arrival_city,
        "departure_city": facts.departure_city,
        "overnight_city": facts.overnight_city,
        "onward_destination": facts.onward_destination,
        "transit_cities": list(facts.transit_cities),
        "return_visit": facts.return_visit,
        "visit_number": facts.visit_number,
        "previous_visit_days": list(facts.previous_visit_days),
        "travel_heavy": facts.travel_heavy,
        "full_leisure_day": facts.full_leisure_day,
        "partial_leisure_day": facts.partial_leisure_day,
        "cruise_onboard_day": facts.cruise_onboard_day,
        "same_city_accommodation_change": facts.same_city_accommodation_change,
        "confirmed_check_in": facts.confirmed_check_in,
        "confirmed_check_out": facts.confirmed_check_out,
        "source_flags": sorted(facts.source_flags),
    }


def build_day_brain_day_report(
    day: str,
    rows: Sequence[Mapping[str, Any]],
    *,
    visit_context: DayVisitContext | None = None,
) -> dict[str, Any]:
    """Return a complete developer report for one itinerary day."""

    facts = build_day_facts(rows, visit_context=visit_context)
    intent = classify_day_intent(facts)
    intro = create_day_intro(rows, visit_context=visit_context)
    leisure = write_leisure_copy(facts, intent)
    issues = find_day_copy_issues(facts=facts, intent=intent, intro=intro, leisure=leisure)
    event_summary = summarize_timeline_events(facts.timeline_events)

    return {
        "day": _clean(day),
        "intent": str(intent),
        "intro": intro,
        "leisure": leisure,
        "qa": {
            "issue_count": len(issues),
            "issues": [_dataclass_payload(issue) for issue in issues],
        },
        "facts": day_facts_payload(facts),
        "timeline_summary": _dataclass_payload(event_summary),
        "timeline_events": [timeline_event_payload(event) for event in facts.timeline_events],
        "accommodation_state": _dataclass_payload(facts.accommodation_state),
        "travel_load": _dataclass_payload(facts.travel_load),
        "schedule_profile": _dataclass_payload(facts.schedule_profile),
        "day_state": _dataclass_payload(facts.day_state),
        "visit_context": _dataclass_payload(visit_context) if visit_context else {},
    }


def build_day_brain_report(grouped_days: Mapping[str, Sequence[Mapping[str, Any]]] | Iterable[tuple[str, Sequence[Mapping[str, Any]]]]) -> dict[str, Any]:
    """Return a Day Brain report for a grouped itinerary."""

    items = list(grouped_days.items()) if isinstance(grouped_days, Mapping) else list(grouped_days)
    grouped = {str(day): list(rows or []) for day, rows in items}
    visit_contexts = build_day_visit_contexts(grouped)
    days = [
        build_day_brain_day_report(day, rows, visit_context=visit_contexts.get(str(day)))
        for day, rows in grouped.items()
    ]
    issue_count = sum(day["qa"]["issue_count"] for day in days)
    return {
        "day_count": len(days),
        "issue_count": issue_count,
        "days": days,
    }


__all__ = [
    "build_day_brain_day_report",
    "build_day_brain_report",
    "day_facts_payload",
    "timeline_event_payload",
]

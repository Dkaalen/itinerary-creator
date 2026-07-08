"""Title Brain for day headings.

Chooses a day title that represents the whole day, not just the first or most
exciting row.
"""

from __future__ import annotations

import re
from typing import Mapping, Sequence

from itinerary_generation.activity_titles import create_client_activity_title, normalize_client_day_title
from itinerary_generation.common import TRANSPORT_TYPES, get_primary_city, get_row_type, has_hotel
from itinerary_generation.day_facts import DayFacts, build_day_facts
from itinerary_generation.day_intent import DayIntent, classify_day_intent
from itinerary_generation.schedule_brain import DayScheduleProfile, build_day_schedule_profile
from itinerary_generation.transport import get_primary_transport_title
from itinerary_generation.transport_domain.routes import get_route_points_for_transport
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
    title = normalize_client_day_title(create_client_activity_title(dict(row)), dict(row))
    return polish_title(_clean(title or row.get("title") or row.get("original_title") or "Experience")).strip(" -:|.,")


def _multi_activity_title(activity_rows: Sequence[Mapping[str, object]]) -> str:
    titles = [_single_activity_title(row) for row in activity_rows[:2]]
    return _join_titles(titles[0] if titles else "", titles[1] if len(titles) > 1 else "")


def _route_destination(rows: Sequence[Mapping[str, object]], facts: DayFacts) -> str:
    for row in rows or []:
        if get_row_type(dict(row)) in {"Train", "Flight", "Cruise", "Ferry", "Transport", "Coach", "Bus"}:
            _origin, destination = get_route_points_for_transport(dict(row))
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
    first = _clean(first).strip(" -:|.,")
    second = _clean(second).strip(" -:|.,")
    if not first:
        return second
    if not second or first.casefold() == second.casefold():
        return first
    combined_lower = f"{first} {second}".lower()
    if first.lower().startswith("arrival in ") and "northern lights" in second.lower() and "cruise" in second.lower():
        return f"{first} & Northern Lights Cruise"
    if "bergen past" in combined_lower and "fløibanen" in combined_lower:
        return "Bergen Walking Tour & Fløibanen"
    if "walrus" in combined_lower and "brewery" in combined_lower:
        return "Walrus Safari and Svalbard Brewery Visit"
    if "reindeer" in combined_lower and "northern lights" in combined_lower:
        return "Reindeer & Sámi Culture and Northern Lights Hunt"
    if first.casefold() in second.casefold():
        return second
    if second.casefold() in first.casefold():
        return first
    title = f"{first} & {second}"
    if len(title) <= max_length:
        return title
    title = f"{first} and {second}"
    if len(title) <= max_length:
        return title
    short_title = f"{_short_title(first)} & {_short_title(second)}"
    return short_title if len(short_title) <= max_length else first


def _travel_title(rows: Sequence[Mapping[str, object]], facts: DayFacts, city: str) -> str:
    primary = get_primary_transport_title([dict(row) for row in rows])
    if primary:
        return primary
    destination = _route_destination(rows, facts) or city
    return f"Travel to {destination}" if destination else "Travel day"


def _arrival_activity_title(city: str, activity_title: str, facts: DayFacts, schedule: DayScheduleProfile) -> str:
    if not activity_title:
        return f"Arrival in {city}" if city else "Arrival"
    if city and city.casefold() == "longyearbyen" and facts.has_flight:
        return f"Journey to Svalbard and {activity_title}"
    if len(activity_title) > 45 and "cruise" not in activity_title.lower():
        return _short_title(activity_title)
    if city and (facts.has_route_transport or schedule.has_evening_activity):
        return _join_titles(f"Arrival in {city}", activity_title)
    return activity_title


def write_day_title(
    rows: Sequence[Mapping[str, object]] | None,
    *,
    visit_context: object | None = None,
    facts: DayFacts | None = None,
    intent: DayIntent | None = None,
    schedule: DayScheduleProfile | None = None,
) -> str:
    """Return a whole-day title from sub-brain facts."""

    row_list = [dict(row) for row in (rows or []) if isinstance(row, Mapping)]
    facts = facts or build_day_facts(row_list, visit_context=visit_context)
    intent = intent or classify_day_intent(facts)
    schedule = schedule or build_day_schedule_profile(row_list)
    city = _city(row_list, facts)
    activities = _activity_rows(row_list)
    raw_day_text = " ".join(
        str(row.get(key) or "")
        for row in row_list
        for key in ("title", "original_title", "details")
    ).lower()

    if "excursion to tallinn" in raw_day_text:
        return "Day Excursion to Tallinn"

    primary_transport_title = get_primary_transport_title(row_list)

    if intent == DayIntent.DEPARTURE_DAY:
        return f"Departure from {city}" if city else "Departure"
    if intent == DayIntent.SAME_CITY_ACCOMMODATION_CHANGE:
        hotel_titles = [
            _clean(row.get("title") or row.get("hotel_name") or row.get("original_title"))
            for row in row_list
            if get_row_type(dict(row)) == "Hotel"
        ]
        for hotel_title in hotel_titles:
            if "snow hotel" in hotel_title.lower() or "snowhotel" in hotel_title.lower():
                if "arctic" in hotel_title.lower():
                    return "Arctic Snow Hotel Stay"
                return f"{polish_title(hotel_title)} Stay"
        if facts.return_visit and "next accommodation" not in raw_day_text:
            return f"Return to {city}" if city else "Return Visit"
        return f"Next Stay in {city}" if city else "Next Stay"
    if intent == DayIntent.ARRIVAL_ONWARD_TRAVEL:
        destination = polish_title(facts.onward_destination or facts.end_city or "")
        return f"Arrival and travel to {destination}" if destination else "Arrival and travel day"

    if facts.has_route_transport and not activities and primary_transport_title and (
        facts.has_train or facts.has_flight or facts.has_ferry or facts.has_cruise
    ):
        return primary_transport_title

    if intent == DayIntent.RETURN_VISIT:
        return f"Return to {city}" if city else "Return Visit"

    if activities and schedule.has_multiple_arranged_activities:
        if schedule.first_activity_title and schedule.last_activity_title:
            title = _join_titles(schedule.first_activity_title, schedule.last_activity_title)
            if title:
                return title
        title = _multi_activity_title(activities)
        if title:
            return title

    if activities and intent == DayIntent.ACTIVITY_PLUS_TRAVEL:
        activity_title = _single_activity_title(activities[0])
        return _arrival_activity_title(city, activity_title, facts, schedule)

    if facts.has_route_transport and not activities:
        transport_from_activity = any(
            str(row.get("source_type") or row.get("type") or "").casefold() == "activity"
            and get_row_type(dict(row)) in TRAVEL_ROW_TYPES
            for row in row_list
        )
        if primary_transport_title and (
            transport_from_activity
            or facts.has_train
            or facts.has_flight
            or facts.has_ferry
            or facts.has_cruise
            or re.search(r"\bcoach\b", primary_transport_title, flags=re.IGNORECASE)
        ):
            return primary_transport_title
        if intent == DayIntent.ARRIVAL_STAY and city:
            return f"Arrival in {city}"
        return _travel_title(row_list, facts, city)

    if intent == DayIntent.ARRIVAL_STAY and city:
        return f"Welcome to {city}" if not facts.return_visit else f"Return to {city}"

    if activities:
        return _single_activity_title(activities[0])

    if intent == DayIntent.FULL_LEISURE_DAY:
        return f"A day at leisure in {city}" if city else "A day at leisure"

    if has_hotel(row_list) and city:
        return f"Welcome to {city}"

    return f"Day in {city}" if city else "Day at leisure"


__all__ = ["write_day_title"]

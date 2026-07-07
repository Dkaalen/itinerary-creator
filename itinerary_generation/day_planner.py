"""Day-level planning before row rendering.

The planner looks at all rows for one itinerary day and decides the client-facing
shape of the day: pattern, title, intro, and a few rendering hints. This keeps
multi-row days from being titled or described by whichever raw row happens to
appear first.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from itinerary_generation.common import get_primary_city, get_row_type, has_hotel
from itinerary_generation.content_engine import is_supplier_day_row
from itinerary_generation.day_intro_planner import _group_tour_intro_from_source, _intro_for_title
from itinerary_generation.day_row_selectors import (
    _activity_rows,
    _all_text,
    _has_text,
    _is_empty_activity,
    _text,
)
from itinerary_generation.day_title_planner import (
    _arrival_title,
    _departure_title,
    _accommodation_led_title,
    _destination_from_transport,
    _hop_on_title,
    _leisure_title,
    _multi_activity_title,
    _single_activity_title,
    _transport_title,
    _travel_activity_title,
    travel_sequence_title,
)
from itinerary_generation.titles import create_day_title
from itinerary_generation.title_brain import write_day_title
from itinerary_generation.nutshell_domain import resolve_nutshell_journey
from itinerary_generation.transport import has_airport_arrival_transfer, has_airport_departure_transfer
from itinerary_generation.transport_domain.routes import get_route_points_for_transport
from itinerary_generation.transport_domain.titles import get_primary_transport_title
from text_polish import polish_title


@dataclass(slots=True)
class DayPlan:
    pattern: str
    title: str = ""
    intro: str = ""
    suppress_free_time: bool = False
    skip_empty_activity_rows: bool = False
    consolidate_travel: bool = False
    warnings: list[str] = field(default_factory=list)


ADMIN_TITLE_PATTERNS = [
    r"\bfinal timing\b",
    r"\bshared in voucher\b",
    r"\bvoucher\b",
    r"\bopening hours\b",
    r"\bincludes?\b",
    r"\btickets?\b.*\bopening\b",
]


def plan_day(rows: list[dict]) -> DayPlan:
    city = polish_title(get_primary_city(rows) or "")
    text = _all_text(rows)
    lower = text.lower()
    row_types = [get_row_type(row) for row in rows]
    activity_rows = _activity_rows(rows)
    travel_rows = [row for row in rows if get_row_type(row) in {"Transfer", "Train", "Flight", "Cruise", "Ferry", "Transport"}]
    has_main_route_transport = any(
        get_row_type(row) in {"Train", "Flight", "Cruise", "Ferry", "Transport"}
        or (
            get_row_type(row) == "Transfer"
            and all(get_route_points_for_transport(row))
            and not has_airport_departure_transfer([row])
        )
        for row in travel_rows
    )

    if any(rt == "Departure" for rt in row_types) or (
        travel_rows
        and not activity_rows
        and not has_hotel(rows)
        and has_airport_departure_transfer(rows)
        and not has_main_route_transport
    ):
        return DayPlan("departure_day", _departure_title(city), "")
    if any(rt == "Arrival" for rt in row_types) or (has_hotel(rows) and not activity_rows and has_airport_arrival_transfer(rows)):
        return DayPlan("arrival_day", _arrival_title(city), "")

    nutshell_journey = next((journey for row in rows if (journey := resolve_nutshell_journey(row)) is not None), None)
    if nutshell_journey is not None:
        title = (
            f"Norway in a Nutshell to {nutshell_journey.destination}"
            if nutshell_journey.destination
            else nutshell_journey.client_title
        )
        if title == "Norway in a Nutshell" and city:
            title = f"Norway in a Nutshell to {city}"
        return DayPlan("norway_in_a_nutshell_day", title, _intro_for_title(title, city, "travel_day"), suppress_free_time=True, consolidate_travel=True)

    if travel_rows and all(get_row_type(row) == "Cruise" for row in rows) and _has_text(rows, "spend time at leisure"):
        title = "At Leisure Onboard the Coastal Cruise"
        return DayPlan("cruise_leisure_day", title, "Enjoy a relaxed day onboard the cruise, with time to take in the coastal scenery, use the ship facilities and ease into life onboard for the day.", suppress_free_time=True)

    if any(get_row_type(row) == "Cruise" and "overnight" in _text(row).lower() for row in travel_rows) and (
        any(rt == "Leisure" for rt in row_types) or any(_is_empty_activity(row) for row in rows)
    ):
        cruise_title = _transport_title(rows)
        destination_match = re.search(r"\bto\s+([A-Za-zÀ-ÿøØåÅäÄöÖ ]+)$", cruise_title, flags=re.IGNORECASE)
        destination = polish_title(destination_match.group(1)) if destination_match else ""
        if city and destination:
            return DayPlan(
                "leisure_overnight_cruise_day",
                f"{city} at Leisure and Overnight Cruise to {destination}",
                f"Enjoy time at leisure in {city} before continuing to the cruise harbor for your overnight journey towards {destination}.",
                skip_empty_activity_rows=True,
            )

    if not activity_rows and not travel_rows and any(rt == "Leisure" for rt in row_types):
        title = _leisure_title(city)
        return DayPlan("leisure_day", title, _intro_for_title(title, city, "leisure_day"), skip_empty_activity_rows=True)

    if not activity_rows and any(_is_empty_activity(row) for row in rows):
        title = _leisure_title(city)
        return DayPlan("leisure_day", title, _intro_for_title(title, city, "leisure_day"), skip_empty_activity_rows=True)

    if has_hotel(rows) and not activity_rows and travel_rows:
        accommodation_title = _accommodation_led_title(rows, city)
        if accommodation_title:
            return DayPlan("stay_day", accommodation_title, _intro_for_title(accommodation_title, city, "stay_day"), suppress_free_time=True)
        sequence_title = travel_sequence_title(rows, city)
        has_self_arranged_flight = any(
            get_row_type(row) == "Flight" and str(row.get("commercial_status") or "").lower() == "self_arranged"
            for row in travel_rows
        )
        if sequence_title and has_self_arranged_flight:
            return DayPlan("travel_day", sequence_title, _intro_for_title(sequence_title, city, "travel_day"), suppress_free_time=True, consolidate_travel=True)
        primary_transport_title = get_primary_transport_title(rows)
        if primary_transport_title and primary_transport_title.lower().startswith("journey to"):
            return DayPlan("travel_day", primary_transport_title, _intro_for_title(primary_transport_title, city, "travel_day"), suppress_free_time=True, consolidate_travel=True)
        if sequence_title:
            return DayPlan("travel_day", sequence_title, _intro_for_title(sequence_title, city, "travel_day"), suppress_free_time=True, consolidate_travel=True)
        transfer_text = " ".join(_text(row).lower() for row in travel_rows)
        if "to your accommodation" in transfer_text or "to your hotel" in transfer_text:
            return DayPlan("arrival_day", f"Arrival in {city}" if city else "Arrival", "")

    if "hop on hop off" in lower or "hop-on hop-off" in lower or "hop on hop" in lower:
        title = _hop_on_title(city)
        return DayPlan("hop_on_city_day", title, _intro_for_title(title, city, "hop_on_city_day"), skip_empty_activity_rows=True)

    if _has_text(rows, "Route Suggested", "Golden Circle Route", "SOUTH COAST WATERFALLS", "SCENIC RETURN DRIVE"):
        # If there is also an activity, keep the activity as title; the route is rendered as a route block.
        if not activity_rows:
            title = f"Scenic drive to {city}" if city else "Scenic self-drive route"
            return DayPlan("self_drive_route_day", title, _intro_for_title(title, city, "self_drive_route_day"), suppress_free_time=True)

    if travel_rows and has_hotel(rows) and activity_rows:
        title = write_day_title(rows) or _travel_activity_title(rows, activity_rows, city)
        if "svalbard" in lower and city.lower() == "longyearbyen":
            intro = f"Welcome to Svalbard. After arrival, the day is organised around {title}."
        elif city:
            intro = f"Welcome to {city}. After arrival and check-in, the day is organised around {title}."
        else:
            intro = f"After the day’s travel arrangements, the main included experience is {title}."
        return DayPlan("travel_activity_day", title, intro, skip_empty_activity_rows=True)

    if len(activity_rows) >= 2:
        title = write_day_title(rows) or _multi_activity_title(activity_rows, city)
        if title:
            return DayPlan("multi_activity_day", title, _intro_for_title(title, city, "multi_activity_day"), skip_empty_activity_rows=True)

    if activity_rows:
        if "tallinn" in lower and ("old town" in lower or "ferry" in lower or "excursion" in lower):
            title = "Day Excursion to Tallinn"
            return DayPlan("single_activity_day", title, _intro_for_title(title, city, "multi_activity_day"), skip_empty_activity_rows=True)
        title = _single_activity_title(activity_rows[0])
        if re.search(r"hop[- ]?on\s+hop[- ]?off", title, flags=re.I):
            title = _hop_on_title(city)
            return DayPlan("hop_on_city_day", title, _intro_for_title(title, city, "hop_on_city_day"), skip_empty_activity_rows=True)
        if is_supplier_day_row(activity_rows[0]):
            source_intro = _group_tour_intro_from_source(title, _text(activity_rows[0]))
            if source_intro:
                return DayPlan("group_tour_day", title, source_intro, skip_empty_activity_rows=True)
        return DayPlan("single_activity_day", title, _intro_for_title(title, city, "single_activity_day"), skip_empty_activity_rows=True)

    if travel_rows:
        primary_transport_title = get_primary_transport_title(rows)
        has_single_route_transfer = len(travel_rows) == 1 and get_row_type(travel_rows[0]) == "Transfer" and all(get_route_points_for_transport(travel_rows[0]))
        if has_single_route_transfer and primary_transport_title:
            origin, destination = get_route_points_for_transport(travel_rows[0])
            intro = f"After check-out, take your arranged transfer from {origin} to {destination} for your onward journey."
            return DayPlan("travel_day", primary_transport_title, intro, suppress_free_time=True, consolidate_travel=True)
        title = primary_transport_title if primary_transport_title and primary_transport_title.lower().startswith("journey to") else (travel_sequence_title(rows, city) or _transport_title(rows))
        if not title:
            dest = _destination_from_transport(rows) or city
            title = f"Travel to {dest}" if dest else "Travel day"
        return DayPlan("travel_day", title, _intro_for_title(title, city, "travel_day"), suppress_free_time=True, consolidate_travel=True)

    if has_hotel(rows) and city:
        title = _accommodation_led_title(rows, city) or f"Welcome to {city}"
        intro = _intro_for_title(title, city, "stay_day")
        return DayPlan("stay_day", title, intro)

    title = _leisure_title(city)
    return DayPlan("leisure_day", title, _intro_for_title(title, city, "leisure_day"), skip_empty_activity_rows=True)


__all__ = [
    "ADMIN_TITLE_PATTERNS",
    "DayPlan",
    "_activity_rows",
    "_all_text",
    "_arrival_title",
    "_departure_title",
    "_destination_from_transport",
    "_group_tour_intro_from_source",
    "_has_text",
    "_hop_on_title",
    "_intro_for_title",
    "_is_empty_activity",
    "_leisure_title",
    "_multi_activity_title",
    "_single_activity_title",
    "_text",
    "_transport_title",
    "_travel_activity_title",
    "plan_day",
]

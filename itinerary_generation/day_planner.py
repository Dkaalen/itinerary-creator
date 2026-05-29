"""Day-level planning before row rendering.

The planner looks at all rows for one itinerary day and decides the client-facing
shape of the day: pattern, title, intro, and a few rendering hints.  This keeps
multi-row days from being titled or described by whichever raw row happens to
appear first.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from itinerary_generation.common import get_primary_city, get_row_type, has_hotel
from itinerary_generation.titles import create_client_activity_title, normalize_client_day_title, create_day_title
from itinerary_generation.transport import get_premium_transport_phrase, get_route_points_for_transport, has_airport_arrival_transfer, has_airport_departure_transfer
from itinerary_generation.content_engine import is_supplier_day_row
from place_aliases import canonicalize_place_name, country_for_place
from text_polish import polish_client_text, polish_title


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


def _text(row: dict) -> str:
    return " ".join(str(row.get(key, "") or "") for key in ["title", "details", "original_title"] if str(row.get(key, "") or "").strip())


def _all_text(rows: list[dict]) -> str:
    return " ".join(_text(row) for row in rows)


def _is_empty_activity(row: dict) -> bool:
    if get_row_type(row) != "Activity":
        return False
    raw = _text(row).strip()
    city = str(row.get("city", "") or "").strip()
    if not raw:
        return True
    cleaned = re.sub(r"\s+", " ", raw).strip(" -:|")
    return bool(city and cleaned.lower() == city.lower())


def _activity_rows(rows: list[dict]) -> list[dict]:
    return [row for row in rows if get_row_type(row) == "Activity" and not _is_empty_activity(row)]


def _has_text(rows: list[dict], *needles: str) -> bool:
    lower = _all_text(rows).lower()
    return any(needle.lower() in lower for needle in needles)


def _clean_title(value: str) -> str:
    title = polish_title(polish_client_text(value)).strip(" -:|")
    title = re.sub(r"\bToday\b\s*$", "", title, flags=re.I).strip(" -:|")
    title = re.sub(r"\b3-4\s*hours\b", "", title, flags=re.I).strip(" -:|")
    title = re.sub(r"\bFjord Cruise\s+Day Trip\b", "Fjord Cruise", title, flags=re.I).strip(" -:|")
    return title


def _destination_from_transport(rows: list[dict]) -> str:
    for row in rows:
        if get_row_type(row) in {"Train", "Flight", "Cruise", "Ferry", "Transfer", "Transport"}:
            _, dest = get_route_points_for_transport(row)
            if dest:
                return polish_title(dest)
    return ""


def _transport_title(rows: list[dict]) -> str:
    for row in rows:
        row_type = get_row_type(row)
        row_text = _text(row)
        if row_type in {"Train", "Flight", "Cruise", "Ferry", "Transport"} or re.search(r"\b(?:train|flight|cruise|ferry|coach|bus)\b", row_text, flags=re.I):
            phrase = get_premium_transport_phrase(row)
            if phrase:
                if row_type == "Train" and "norway in a nutshell" not in row_text.lower():
                    _, destination = get_route_points_for_transport(row)
                    if destination:
                        if "overnight" in row_text.lower():
                            return f"Overnight train to {polish_title(destination)}"
                        return f"Train to {polish_title(destination)}"
                return polish_title(phrase)
    for row in rows:
        if get_row_type(row) == "Transfer":
            phrase = get_premium_transport_phrase(row)
            if phrase:
                return polish_title(phrase)
    return ""


def _single_activity_title(row: dict) -> str:
    title = normalize_client_day_title(create_client_activity_title(row), row)
    return _clean_title(title)


def _multi_activity_title(rows: list[dict], city: str) -> str:
    text = _all_text(rows).lower()
    if "mostraumen" in text and ("fløibanen" in text or "floibanen" in text):
        return "Bergen Fjord Cruise & Fløibanen"
    if ("walking" in text or "on foot" in text) and ("boat" in text or "fjord" in text) and ("fløibanen" in text or "floibanen" in text):
        return "Bergen Walking, Boat Tour & Fløibanen"
    if "walking" in text and ("fjord cruise" in text or "silent electric" in text or "oslo fjord" in text or "oslofjord" in text):
        return "Oslo Walking Tour & Fjord Cruise"
    if "husky" in text and "reindeer" in text:
        return "Husky & Reindeer Experiences"
    if "food tour" in text and city:
        return f"{city} Food Tour"
    return ""


def _hop_on_title(city: str) -> str:
    return f"Explore {city} at your own pace" if city else "Explore the city at your own pace"


def _leisure_title(city: str) -> str:
    return f"A day at leisure in {city}" if city else "A day at leisure"


def _arrival_title(city: str) -> str:
    country = country_for_place(city) if city else ""
    if country == "Iceland":
        return "Welcome to Iceland"
    return f"Welcome to {city}" if city else "Welcome"


def _departure_title(city: str) -> str:
    return f"Departure from {city}" if city else "Departure"


def _group_tour_intro_from_source(title: str, source: str) -> str:
    lower = f"{title} {source}".lower()
    if "whale" in lower and "hauganes" in lower:
        return "Your guided group tour continues today to Hauganes for Whale Watching before returning to Reykjavík. The day is organised around the included boat experience and the final guided route back to the capital."
    return ""

def _intro_for_title(title: str, city: str, pattern: str) -> str:
    if pattern == "leisure_day":
        return f"Enjoy a slower day in {city}, with time to explore independently, relax, or add optional experiences that suit your interests." if city else "Enjoy a slower day, with time to explore independently or relax."
    if pattern == "multi_activity_day":
        return f"Today combines complementary experiences in {city}, with the schedule arranged so the day feels varied but easy to follow." if city else "Today combines complementary experiences, with the schedule arranged so the day feels varied but easy to follow."
    if pattern == "travel_day":
        dest = re.sub(r"^(?:Train|Flight|Cruise|Coach Transfer|Scenic Train Transfer|Panoramic Coach Transfer)\s+(?:from\s+.+?\s+)?to\s+", "", title, flags=re.I)
        return f"The journey continues towards {dest}, with the travel arrangements structured to keep the route clear, comfortable, and easy to follow." if dest and dest != title else "The journey continues today, with the travel arrangements structured to keep the route clear, comfortable, and easy to follow."
    if pattern == "self_drive_route_day":
        return f"Today’s self-drive route is arranged to keep the journey clear and scenic, with suggested stops and overnight plans laid out in a simple way."
    if pattern == "hop_on_city_day":
        return f"Use the day flexibly to explore {city} at your own pace, with sightseeing transport arranged to make the city’s main areas easy to reach." if city else "Use the day flexibly to explore at your own pace, with sightseeing transport arranged to make the main areas easy to reach."
    if pattern == "single_activity_day":
        return f"Today is centred on {title} in {city}, with the surrounding schedule kept clear and comfortable." if city and city.lower() not in title.lower() else f"Today is centred on {title}, with the surrounding schedule kept clear and comfortable."
    return ""


def plan_day(rows: list[dict]) -> DayPlan:
    city = polish_title(get_primary_city(rows) or "")
    text = _all_text(rows)
    lower = text.lower()
    row_types = [get_row_type(row) for row in rows]
    activity_rows = _activity_rows(rows)
    travel_rows = [row for row in rows if get_row_type(row) in {"Transfer", "Train", "Flight", "Cruise", "Ferry", "Transport"}]

    if any(rt == "Departure" for rt in row_types) or (travel_rows and not activity_rows and not has_hotel(rows) and has_airport_departure_transfer(rows)):
        return DayPlan("departure_day", _departure_title(city), "")
    if any(rt == "Arrival" for rt in row_types) or (has_hotel(rows) and not activity_rows and has_airport_arrival_transfer(rows)):
        return DayPlan("arrival_day", _arrival_title(city), "")

    looks_nutshell = _has_text(rows, "norway in a nutshell") or (re.search(r"fl[åa]m\s+train|fl[åa]m\s+railway|nærøyfjord|naeroyfjord", lower, flags=re.I) and re.search(r"luggage transfer|fjord cruise|myrdal|gudvangen", lower, flags=re.I))
    if looks_nutshell:
        title = create_day_title(rows)
        m = re.search(r"Norway in a Nutshell from .+ to ([A-Za-zÀ-ÿøØåÅäÄöÖ]+)$", title)
        if m:
            title = f"Norway in a Nutshell to {polish_title(m.group(1))}"
        if title == "Norway in a Nutshell" and city:
            title = f"Norway in a Nutshell to {city}"
        return DayPlan("norway_in_a_nutshell_day", title, _intro_for_title(title, city, "travel_day"), suppress_free_time=True, consolidate_travel=True)

    if travel_rows and all(get_row_type(row) == "Cruise" for row in rows) and _has_text(rows, "spend time at leisure"):
        title = "Spend time at leisure onboard the cruise"
        return DayPlan("cruise_leisure_day", title, "Enjoy a relaxed day onboard the cruise, with time to take in the coastal scenery, use the ship facilities and settle into the rhythm of the voyage.", suppress_free_time=True)

    if not activity_rows and not travel_rows and any(rt == "Leisure" for rt in row_types):
        title = _leisure_title(city)
        return DayPlan("leisure_day", title, _intro_for_title(title, city, "leisure_day"), skip_empty_activity_rows=True)

    if not activity_rows and any(_is_empty_activity(row) for row in rows):
        title = _leisure_title(city)
        return DayPlan("leisure_day", title, _intro_for_title(title, city, "leisure_day"), skip_empty_activity_rows=True)

    if "hop on hop off" in lower or "hop-on hop-off" in lower or "hop on hop" in lower:
        title = _hop_on_title(city)
        return DayPlan("hop_on_city_day", title, _intro_for_title(title, city, "hop_on_city_day"), skip_empty_activity_rows=True)

    if _has_text(rows, "Route Suggested", "Golden Circle Route", "SOUTH COAST WATERFALLS", "SCENIC RETURN DRIVE"):
        # If there is also an activity, keep the activity as title; the route is rendered as a route block.
        if not activity_rows:
            title = f"Scenic drive to {city}" if city else "Scenic self-drive route"
            return DayPlan("self_drive_route_day", title, _intro_for_title(title, city, "self_drive_route_day"), suppress_free_time=True)

    if len(activity_rows) >= 2:
        title = _multi_activity_title(activity_rows, city)
        if title:
            return DayPlan("multi_activity_day", title, _intro_for_title(title, city, "multi_activity_day"), skip_empty_activity_rows=True)

    if activity_rows:
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
        title = _transport_title(rows)
        if not title:
            dest = _destination_from_transport(rows) or city
            title = f"Travel to {dest}" if dest else "Travel day"
        return DayPlan("travel_day", title, _intro_for_title(title, city, "travel_day"), suppress_free_time=True, consolidate_travel=True)

    if has_hotel(rows) and city:
        title = f"Stay in {city}"
        return DayPlan("stay_day", title, f"This is part of your stay in {city}, with the day’s arrangements laid out clearly so the experience feels relaxed and easy to follow.")

    title = _leisure_title(city)
    return DayPlan("leisure_day", title, _intro_for_title(title, city, "leisure_day"), skip_empty_activity_rows=True)

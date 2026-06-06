"""Client-facing title helpers for day planning."""

from __future__ import annotations

import re

from itinerary_generation.common import get_row_type
from itinerary_generation.day_row_selectors import _all_text, _text
from itinerary_generation.titles import create_client_activity_title, normalize_client_day_title
from itinerary_generation.transport import get_transport_route_phrase, get_route_points_for_transport
from place_aliases import country_for_place
from text_polish import polish_client_text, polish_title


def _clean_title(value: str) -> str:
    title = polish_title(polish_client_text(value)).strip(" -:|")
    title = re.sub(r"\bToday\b\s*$", "", title, flags=re.I).strip(" -:|")
    title = re.sub(r"\b3-4\s*hours\b", "", title, flags=re.I).strip(" -:|")
    title = re.sub(r"\bFjord Cruise\s+Day Trip\b", "Fjord Cruise", title, flags=re.I).strip(" -:|")
    title = re.sub(r"\bWalrus Safari Boat Tour\b", "Walrus Safari", title, flags=re.I).strip(" -:|")
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
        if row_type == "Transfer" and re.search(r"\bself\s+transfer\b|\b(?:hotel|accommodation)\s+to\s+(?:bus|coach|train|station)", row_text, flags=re.I):
            # Local access transfers should not outrank the main intercity
            # movement when a coach/train/flight row follows on the same day.
            continue
        if row_type in {"Train", "Flight", "Cruise", "Ferry", "Transport"} or (
            row_type != "Transfer" and re.search(r"\b(?:train|flight|cruise|ferry|coach|bus)\b", row_text, flags=re.I)
        ) or (
            row_type == "Transfer"
            and re.search(r"\b(?:coach|bus)\b", row_text, flags=re.I)
            and not re.search(r"\bself\s+transfer\b|\b(?:hotel|accommodation)\s+to\s+(?:bus|coach|train|station)", row_text, flags=re.I)
        ):
            phrase = get_transport_route_phrase(row)
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
            phrase = get_transport_route_phrase(row)
            if phrase:
                return polish_title(phrase)
    return ""


def _single_activity_title(row: dict) -> str:
    title = normalize_client_day_title(create_client_activity_title(row), row)
    return _clean_title(title)


def _join_two_titles(first: str, second: str) -> str:
    first = _clean_title(first)
    second = _clean_title(second)
    if not first:
        return second
    if not second or second.lower() == first.lower():
        return first
    second_lower = second.lower()
    first_lower = first.lower()
    if second_lower.startswith(first_lower) or first_lower.startswith(second_lower):
        return first if len(first) >= len(second) else second
    return f"{first} and {second}"


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
    if "tallinn" in text and ("excursion" in text or "ferry" in text or "old town" in text):
        return "Day Excursion to Tallinn"

    titles = [_single_activity_title(row) for row in rows[:2]]
    title = _join_two_titles(titles[0] if titles else "", titles[1] if len(titles) > 1 else "")
    return title if len(title) <= 82 else (titles[0] if titles else "")


def _travel_activity_title(rows: list[dict], activity_rows: list[dict], city: str) -> str:
    """Title a day that is both a travel/check-in day and an activity day."""

    if not activity_rows:
        return ""
    activity_title = _single_activity_title(activity_rows[0])
    transport_text = _all_text(rows)
    destination = _destination_from_transport(rows) or city
    if re.search(r"\bsvalbard\b", transport_text, flags=re.I) and city and "longyearbyen" in city.lower():
        if activity_title.lower().startswith("longyearbyen"):
            return f"Journey to Svalbard and {activity_title}"
        return f"Journey to Svalbard and {activity_title}"
    # When a day combines arrival/check-in logistics with a real included
    # experience, the client title should be the experience. Route details are
    # already shown under Travel Arrangements; turning them into the title creates
    # weak labels such as "Journey to Airport and Northern Lights Chase".
    return activity_title


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

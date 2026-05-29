"""Client-facing title helpers for day planning."""

from __future__ import annotations

import re

from itinerary_generation.common import get_row_type
from itinerary_generation.day_row_selectors import _all_text, _text
from itinerary_generation.titles import create_client_activity_title, normalize_client_day_title
from itinerary_generation.transport import get_premium_transport_phrase, get_route_points_for_transport
from place_aliases import country_for_place
from text_polish import polish_client_text, polish_title


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

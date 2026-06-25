"""Arrival, departure and destination-stay intro helpers."""

from __future__ import annotations

import re

from itinerary_generation.common import get_row_type
from itinerary_generation.day_arrival_text import _arrival_display_destination
from itinerary_generation.destination_copy import destination_stay_intro
from itinerary_generation.transport_model import get_transport_source_text
from itinerary_generation.transport_safety import normalize_transport_place


def _explicit_transfer_airport(day_rows) -> str:
    """Return an explicitly mentioned airport from transfer rows, preserving input."""

    for row in day_rows:
        if get_row_type(row) != "Transfer":
            continue
        text = get_transport_source_text(row)
        match = re.search(
            r"\b(?:to|from)\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?\s+Airport)\b",
            text,
            flags=re.IGNORECASE,
        )
        if not match:
            all_airports = re.findall(
                r"\b([A-ZÅÄÖÆØ][A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{1,40}?\s+Airport)\b",
                text,
            )
            if all_airports:
                airport = normalize_transport_place(all_airports[-1])
                if airport:
                    return airport
            continue
        airport = normalize_transport_place(match.group(1))
        if airport and airport.lower() not in {"airport", "the airport"}:
            return airport
    return ""


def _welcome_arrival_intro(city: str, detail_level: str, *, with_activity: bool = False, visit_context=None) -> str:
    """Return the correct welcome/stay line for an arrival or return-arrival day."""

    destination = _arrival_display_destination(city)
    if with_activity:
        prefix = "Return to" if getattr(visit_context, "is_return_visit", False) else "Welcome to"
        return f"{prefix} {destination}."
    return destination_stay_intro(city, detail_level, visit_context=visit_context)


def _has_destination_hotel(day_rows: list[dict], city: str) -> bool:
    """Return True when a hotel row is explicitly in the target destination city."""

    city_key = str(city or "").strip().lower()
    if not city_key:
        return False
    return any(
        get_row_type(row) == "Hotel" and str(row.get("city", "")).strip().lower() == city_key
        for row in day_rows
    )


__all__ = ["_explicit_transfer_airport", "_has_destination_hotel", "_welcome_arrival_intro"]

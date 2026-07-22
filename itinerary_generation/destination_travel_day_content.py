"""Destination-aware travel-day fallback prose."""
from __future__ import annotations

import re

from itinerary_generation.destination_arrival_content import arrival_focus_for_destination
from itinerary_generation.destination_content_lookup import resolve_destination
from text_polish import polish_title

def _mode_label(mode: object) -> str:
    value = str(mode or "").strip().lower()
    if value == "coach":
        return "coach"
    if value == "bus":
        return "coach"
    if value == "train":
        return "rail"
    if value == "flight":
        return "flight"
    if value in {"ferry", "cruise"}:
        return value
    return value


def _clean_place(value: object) -> str:
    text = polish_title(str(value or "").strip())
    text = re.sub(r"\s+", " ", text).strip()
    return text


def travel_day_intro(origin: object, destination: object, mode: object = "") -> str:
    """Return a premium generic travel-day intro for registered destinations."""

    origin_text = _clean_place(origin)
    destination_record = resolve_destination(destination).record
    destination_text = destination_record.name if destination_record else resolve_destination(destination).name
    if not destination_text:
        return "Today is arranged as a clear travel day, with the route and arrival details grouped below."

    focus = arrival_focus_for_destination(destination_record)
    mode_text = _mode_label(mode)
    if origin_text and origin_text.lower() == destination_text.lower():
        origin_text = ""

    destination_focus = f"{destination_text}’s {focus}"
    if origin_text and mode_text:
        return f"Travel from {origin_text} to {destination_text} by {mode_text}, with the day shaped around the move into {destination_focus}."
    if origin_text:
        return f"Travel from {origin_text} to {destination_text}, with the day shaped around the move into {destination_focus}."
    if mode_text:
        return f"Travel to {destination_text} by {mode_text}, with the day shaped around {destination_focus}."
    return f"Travel to {destination_text}, with the day shaped around {destination_focus}."

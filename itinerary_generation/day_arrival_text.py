"""Arrival wording helpers for day intro text."""

from __future__ import annotations

from itinerary_generation.common import get_row_type
from itinerary_generation.transport import get_first_transfer_title
from place_aliases import country_for_place


def _arrival_display_destination(city):
    """Use a warm destination label for arrival intros."""
    country = country_for_place(city)
    if country == "Iceland":
        return "Iceland"
    return city or "the area"


def _arrival_transfer_phrase(day_rows):
    for row in day_rows:
        if get_row_type(row) != "Transfer":
            continue
        title = get_first_transfer_title([row]) or row.get("title", "")
        lower = str(title).lower()
        if "self" in lower:
            return "After arrival, make your own way to your accommodation."
        if "flybus" in lower or "shuttle" in lower:
            return "On arrival, your arranged Flybus transfer will take you from the airport towards your accommodation area."
        if "private" in lower or "transfer" in lower:
            return "On arrival, your arranged transfer will take you from the airport to your accommodation."
    return "On arrival, make your way to your accommodation and check in."



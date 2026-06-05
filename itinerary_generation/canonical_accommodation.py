"""Canonical accommodation block builder."""

from __future__ import annotations

import re

from itinerary_generation.canonical_helpers import _row_id, _source_text
from itinerary_generation.canonical_model import CanonicalBlock
from text_polish import polish_client_text, polish_hotel_name, polish_title
from itinerary_generation.accommodation_display_helpers import meal_phrase, plural_nights


def canonical_accommodation_block(row: dict) -> CanonicalBlock:
    hotel_name = polish_hotel_name(row.get("hotel_name") or row.get("title") or "Accommodation as listed")
    nights = plural_nights(row.get("hotel_nights", ""))
    room_category = polish_client_text(row.get("room_category") or "")
    if room_category.lower().strip() in {"self arranged", "self-arranged", "n/a", "na"}:
        room_category = ""
    meal = meal_phrase(row.get("meal_plan", ""))
    city = polish_title(row.get("city", ""))

    accommodation_line = polish_client_text(hotel_name)
    if re.search(r"\bor\s+similar\b", _source_text(row), flags=re.IGNORECASE):
        if not re.search(r"\bor\s+similar\b", accommodation_line, flags=re.IGNORECASE):
            accommodation_line += " or similar"
    if city and city.lower() not in accommodation_line.lower():
        accommodation_line += f" in {city}"
    if nights:
        accommodation_line += f" for {nights}"

    lines: list[str] = []
    if room_category:
        line = f"Room category: {room_category}"
        if meal:
            line += f", {meal}"
        lines.append(line)
    elif meal:
        lines.append(meal.capitalize())

    return CanonicalBlock(
        kind="accommodation",
        row_id=_row_id(row),
        section_title="Overnight" if row.get("is_group_tour_accommodation") else "Accommodation",
        title=accommodation_line,
        lines=lines,
        source_row_ids=[_row_id(row)],
    )

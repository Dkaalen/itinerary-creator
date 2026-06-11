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
    raw_room_category = str(row.get("room_category") or "")
    room_category = polish_client_text(raw_room_category)
    # Room categories are source product names. Undo broad description-level
    # substitutions that are safe for prose but unsafe for room names.
    room_category = re.sub(r"\bNorthern Lights\s+Nest\b", "Aurora Nest", room_category, flags=re.IGNORECASE)
    if re.search(r"\bpremium\s+double\s+igloo\b", raw_room_category, flags=re.IGNORECASE):
        if not re.search(r"\bpremium\s+double\s+igloo\b", room_category, flags=re.IGNORECASE):
            room_category = re.sub(r"\bdouble\s+igloo\b", "Premium Double Igloo", room_category, flags=re.IGNORECASE)
    if room_category.lower().strip() in {"self arranged", "self-arranged", "n/a", "na"}:
        room_category = ""
    meal = meal_phrase(row.get("meal_plan", ""))
    city = polish_title(row.get("city", ""))
    star_rating = str(row.get("star_rating") or "").strip()

    protected_hotel_name = re.sub(r"\bAurora\b", "__HOTEL_AURORA__", hotel_name, flags=re.IGNORECASE)
    accommodation_line = polish_client_text(protected_hotel_name).replace("__HOTEL_AURORA__", "Aurora")
    if star_rating and not re.search(r"\b[2-5]\s*[- ]?star\b", accommodation_line, flags=re.IGNORECASE):
        accommodation_line = f"{star_rating}-star {accommodation_line}"
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

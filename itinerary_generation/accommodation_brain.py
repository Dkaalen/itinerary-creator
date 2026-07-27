"""Accommodation Brain.

Owns factual accommodation wording: star-level safety, stay labels, and
check-in/check-out certainty. This module does not write day intros.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping

from itinerary_generation.accommodation_display_helpers import meal_phrase, plural_nights
from shared.source_text_cleanup import clean_supplier_text
from text_polish import polish_client_text, polish_hotel_name, polish_title

_STAR_RE = re.compile(r"\b(?P<rating>[2-5](?:\s*/\s*[2-5])?)\s*[- ]?star\b", re.IGNORECASE)


@dataclass(frozen=True)
class AccommodationBrainResult:
    """Client-safe facts for a single accommodation row."""

    hotel_name: str = ""
    city: str = ""
    star_rating: str = ""
    star_rating_is_range: bool = False
    nights: str = ""
    room_category: str = ""
    meal: str = ""
    title: str = ""
    room_line: str = ""
    warnings: tuple[str, ...] = ()


def normalize_star_rating(value: object, *, source_text: object = "") -> str:
    """Return a source-owned star rating, preserving ranges such as 3/4."""

    raw = str(value or "").strip()
    source = str(source_text or "")
    for candidate in (source, raw):
        match = _STAR_RE.search(candidate)
        if match:
            return re.sub(r"\s+", "", match.group("rating"))
    if re.fullmatch(r"[2-5](?:\s*/\s*[2-5])?", raw):
        return re.sub(r"\s+", "", raw)
    return ""


def _has_star_label(value: str) -> bool:
    return bool(_STAR_RE.search(value or ""))


def _generic_hotel_label(star_rating: str) -> str:
    if star_rating:
        return f"{star_rating}-star hotel"
    return "Accommodation as listed"


def accommodation_brain_for_row(row: Mapping[str, object] | None) -> AccommodationBrainResult:
    """Return client-safe accommodation display decisions for one row."""

    row = row or {}
    source_text = " ".join(
        str(row.get(key) or "")
        for key in ("raw", "details", "original_title", "title", "hotel_name")
    )
    star_rating = normalize_star_rating(row.get("star_rating"), source_text=source_text)
    hotel_name = polish_hotel_name(row.get("hotel_name") or row.get("title") or _generic_hotel_label(star_rating))
    hotel_name = clean_supplier_text(hotel_name)
    generic_label = _generic_hotel_label(star_rating)
    generic_match = re.search(r"\bcentrally\s+located\s+[2-5](?:\s*/\s*[2-5])?\s*[- ]?star\s+hotel\b", source_text, flags=re.IGNORECASE)
    if generic_match and hotel_name.casefold() == generic_label.casefold():
        hotel_name = clean_supplier_text(generic_match.group(0)).capitalize()
    if not hotel_name:
        hotel_name = generic_label
    city = polish_title(str(row.get("city") or "").strip())
    nights = plural_nights(row.get("hotel_nights", ""))
    raw_room_category = str(row.get("room_category") or "")
    room_category = polish_client_text(clean_supplier_text(raw_room_category))
    if room_category.lower().strip() in {"self arranged", "self-arranged", "n/a", "na"}:
        room_category = ""
    meal = meal_phrase(row.get("meal_plan", ""))

    title = clean_supplier_text(hotel_name)
    if star_rating and not _has_star_label(title):
        title = f"{star_rating}-star {title}"
    if city and city.lower() not in title.lower():
        title = f"{title} in {city}"
    if nights:
        title = f"{title} for {nights}"

    room_line = ""
    if room_category:
        room_line = f"Room category: {room_category}"
        if meal:
            room_line += f", {meal}"
    elif meal:
        room_line = meal.capitalize()

    warnings: list[str] = []
    if "/" in star_rating:
        warnings.append("star_rating_range_preserved")

    return AccommodationBrainResult(
        hotel_name=hotel_name,
        city=city,
        star_rating=star_rating,
        star_rating_is_range="/" in star_rating,
        nights=nights,
        room_category=room_category,
        meal=meal,
        title=title,
        room_line=room_line,
        warnings=tuple(warnings),
    )


__all__ = ["AccommodationBrainResult", "accommodation_brain_for_row", "normalize_star_rating"]

"""Accommodation-signal helpers for day facts."""

from __future__ import annotations

from typing import Any, Mapping

from itinerary_generation.common import get_row_type
from itinerary_generation.day_city_facts import row_text

ACCOMMODATION_WORDS = ("hotel", "accommodation", "resort", "cabin", "igloo", "lodge", "apartment")


def is_accommodation_change_row(row: Mapping[str, Any]) -> bool:
    """Return whether a row can indicate an accommodation movement/change."""

    text = row_text(row).lower()
    row_type = get_row_type(dict(row))
    if row_type == "Hotel":
        return True
    if row_type == "Transfer":
        return any(marker in text for marker in ("to your accommodation", "to your hotel", "between accommodations", "hotel to hotel", "next stay"))
    return False


def confirmed_check_in(has_accommodation: bool, same_city_change: bool, has_arrival: bool, overnight_city: str, all_text: str, accommodation_state: object) -> bool:
    """Return whether copy may factually mention check-in."""

    return bool(
        getattr(accommodation_state, "check_in_confirmed", False)
        or (
            has_accommodation
            and not same_city_change
            and (has_arrival or overnight_city or "check-in" in all_text or "check in" in all_text)
        )
    )


def confirmed_check_out(has_accommodation: bool, has_departure: bool, all_text: str, accommodation_state: object) -> bool:
    """Return whether copy may factually mention check-out."""

    return bool(
        getattr(accommodation_state, "check_out_confirmed", False)
        or (has_accommodation and (has_departure or "check-out" in all_text or "check out" in all_text))
    )


__all__ = ["ACCOMMODATION_WORDS", "confirmed_check_in", "confirmed_check_out", "is_accommodation_change_row"]

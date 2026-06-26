"""Accommodation wording helpers for UI rendering."""

from __future__ import annotations


def plural_nights(value):
    value = str(value or "").strip()

    if not value:
        return ""

    if value == "1":
        return "1 night"

    return f"{value} nights"


def meal_phrase(value):
    value = str(value or "").strip()

    if not value:
        return ""

    lower = value.lower()

    if lower.startswith("with ") or lower.startswith("without "):
        return value

    if lower == "breakfast":
        return "breakfast included"
    if lower == "breakfast and dinner":
        return "breakfast and dinner included"
    if lower in ["dinner", "half board", "full board"]:
        return f"{lower} included"
    if lower == "room only":
        return "room only"
    if lower == "self catering":
        return "self-catering"

    return f"with {value}"

def is_self_arranged_accommodation(row: dict | None) -> bool:
    """Return True for hotel/accommodation rows that are explicitly self-arranged."""

    row = row or {}
    row_type = str(row.get("effective_type") or row.get("type") or "")
    if row_type != "Hotel":
        return False
    status = str(row.get("commercial_status") or "").strip().lower()
    text = " ".join(
        str(row.get(key) or "")
        for key in ("title", "hotel_name", "details", "original_title", "raw")
    ).lower()
    return status == "self_arranged" or "self arranged" in text or "self-arranged" in text


def self_arranged_accommodation_label(row: dict | None, *, include_nights: bool = True) -> str:
    """Client-facing label for accommodation arranged outside the package."""

    row = row or {}
    city = str(row.get("city") or "").strip()
    label = f"Self-arranged accommodation in {city}" if city else "Self-arranged accommodation"
    if include_nights:
        nights = plural_nights(row.get("hotel_nights", ""))
        if nights:
            label += f" for {nights}"
    return label

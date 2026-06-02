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

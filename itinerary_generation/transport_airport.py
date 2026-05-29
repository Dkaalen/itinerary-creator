"""Airport-transfer day detection helpers."""

from __future__ import annotations

from itinerary_generation.common import get_row_type


def has_airport_arrival_transfer(day_rows):
    text = " ".join(f'{row.get("title", "")} {row.get("details", "")}' for row in day_rows).lower()
    return (
        "airport" in text
        and (
            "to hotel" in text
            or "to accommodation" in text
            or "to your accommodation" in text
            or "to city centre" in text
            or "to city center" in text
        )
    )


def has_airport_departure_transfer(day_rows):
    text = " ".join(f'{row.get("title", "")} {row.get("details", "")}' for row in day_rows).lower()
    return ("airport" in text and ("hotel to" in text or "accommodation to" in text or "to airport" in text))


def has_only_departure_arrangements(day_rows):
    """True when a day is essentially only final airport/departure logistics."""
    if not day_rows:
        return False

    allowed_types = {"Transfer", "Departure"}
    row_types = {get_row_type(row) for row in day_rows}

    if not row_types.issubset(allowed_types):
        return False

    return has_airport_departure_transfer(day_rows) or any(get_row_type(row) == "Departure" for row in day_rows)

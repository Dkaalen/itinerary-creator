"""Context-aware normalization helpers for itinerary rows.

These helpers run after individual rows have been normalized. They use nearby
rows to fill safe missing context, improve repeated activity labels, and correct
travel wording that cannot be decided from one row alone.
"""

from __future__ import annotations

import copy
import re
from collections import Counter

from place_aliases import canonicalize_place_name, is_likely_service_text

from normalizer_modules.text_utils import get_row_type, text_blob


_CONTEXT_ROUTE_TYPES = {
    "Hotel",
    "Activity",
    "Transfer",
    "Transport",
    "Train",
    "Flight",
    "Cruise",
    "Ferry",
    "Departure",
}


_FILLABLE_CONTEXT_TYPES = {"Hotel", "Activity", "Arrival", "Departure", "Leisure"}


def add_repeated_activity_context(rows: list[dict]) -> list[dict]:
    """Add inclusion labels for repeated activities when city context is useful."""

    titles = [row.get("title", "") for row in rows if get_row_type(row) == "Activity" and row.get("title")]
    counts = Counter(titles)
    updated = []
    for row in rows:
        row = copy.deepcopy(row)
        if get_row_type(row) == "Activity" and counts.get(row.get("title", ""), 0) > 1:
            city = canonicalize_place_name(row.get("city", ""))
            title = row.get("title", "")
            if city and f" in {city}" not in title and title.lower().startswith("northern lights"):
                row["inclusion_title"] = f"{title} in {city}"
        updated.append(row)
    return updated


def _day_number_value(value: str) -> int:
    match = re.search(r"\d+", str(value or ""))
    return int(match.group(0)) if match else 0


def _next_main_city(rows: list[dict], current_index: int) -> str:
    current_day = _day_number_value(rows[current_index].get("day", ""))
    for later in rows[current_index + 1 :]:
        later_day = _day_number_value(later.get("day", ""))
        if later_day and current_day and later_day <= current_day:
            continue
        city = canonicalize_place_name(later.get("city", ""))
        if city and get_row_type(later) in _CONTEXT_ROUTE_TYPES:
            return city
    return ""


def apply_contextual_travel_corrections(rows: list[dict]) -> list[dict]:
    """Correct travel wording that depends on surrounding rows."""

    updated = [copy.deepcopy(row) for row in rows or []]
    previous_overnight_destination = ""

    for index, row in enumerate(updated):
        row_type = get_row_type(row)
        full = text_blob(row).lower()

        if row_type == "Train" and "overnight" in full and "train" in full:
            next_city = _next_main_city(updated, index)
            row_city = canonicalize_place_name(row.get("city", ""))
            if next_city and next_city != row_city:
                row["title"] = f"Overnight Train to {next_city}"
                previous_overnight_destination = next_city
            else:
                previous_overnight_destination = row_city or next_city
            continue

        if row_type == "Transfer":
            title_lower = f'{row.get("title", "")} {row.get("original_title", "")} {row.get("details", "")}'.lower()
            city = canonicalize_place_name(row.get("city", ""))
            day = row.get("day", "")
            same_day_has_hotel = any(
                other is not row and other.get("day") == day and get_row_type(other) == "Hotel"
                for other in updated
            )
            if (
                "hotel to station" in title_lower
                and previous_overnight_destination
                and city == previous_overnight_destination
                and same_day_has_hotel
            ):
                row["title"] = "Private transfer from the station to your hotel"
                row["original_title"] = row.get("original_title") or "Private Hotel to Station"

            same_day_arrival_flight = any(
                other is not row
                and other.get("day") == day
                and get_row_type(other) == "Flight"
                and city
                and (
                    canonicalize_place_name(other.get("city", "")) == city
                    or re.search(rf"\bto\s+{re.escape(city)}\b", text_blob(other), flags=re.IGNORECASE)
                )
                for other in updated
            )
            if same_day_has_hotel and same_day_arrival_flight and re.search(
                r"\bhotel\s+to\s+airport\b|\bfrom\s+hotel\s+to\s+airport\b", title_lower
            ):
                row["title"] = (
                    f"Private transfer from {city} Airport to your accommodation"
                    if city
                    else "Private transfer from the airport to your accommodation"
                )
                row["original_title"] = row.get("original_title") or "Private Hotel to Airport"

    return updated


def fill_missing_context_cities(rows: list[dict]) -> list[dict]:
    """Fill safe missing city values from nearby itinerary context.

    Some supplier sheets leave the city column empty on activity/hotel rows
    because the city is implied by the previous or same-day row. Filling these
    rows prevents summary chapters such as "Journey" and day headers with no
    city, while avoiding transport rows where multiple route cities may appear.
    """

    updated = [copy.deepcopy(row) for row in rows or []]
    city_by_day: dict[str, str] = {}

    for row in updated:
        city = canonicalize_place_name(row.get("city", ""))
        if (
            city
            and get_row_type(row) in _FILLABLE_CONTEXT_TYPES
            and not is_likely_service_text(city)
            and city.lower() not in {"accommodation", "journey"}
        ):
            city_by_day.setdefault(row.get("day", ""), city)

    previous_city = ""
    for row in updated:
        row_type = get_row_type(row)
        city = canonicalize_place_name(row.get("city", ""))
        if city and not is_likely_service_text(city) and city.lower() not in {"accommodation", "journey"}:
            previous_city = city
            continue
        if city.lower() in {"accommodation", "journey"}:
            row["city"] = ""
        if row_type in _FILLABLE_CONTEXT_TYPES:
            inferred = city_by_day.get(row.get("day", "")) or previous_city
            if inferred:
                row["city"] = inferred
                city_by_day.setdefault(row.get("day", ""), inferred)
                previous_city = inferred
    return updated

"""
normalizer.py

Post-parser normalization for itinerary rows.

This layer keeps the parser focused on extraction and the generator focused on
rendering. It makes parsed rows safer and more client-facing before they reach
preview/PDF generation.
"""

from __future__ import annotations

import copy
import re
from collections import Counter

import diagnostics
from place_aliases import canonicalize_place_name, is_likely_service_text, is_known_place
from text_polish import polish_client_text, polish_hotel_name, polish_inclusion_items, polish_inclusion_item, polish_title, expand_time_with_duration, format_duration_display


from normalizer_modules.text_utils import clean_space, get_row_type, text_blob, _lower_key
from normalizer_modules.hotels import (
    clean_hotel_name_from_source,
    extract_star_level,
    is_placeholder_hotel_name,
    normalize_hotel_row,
    normalize_meal_plan,
    normalize_room_category,
    _normalize_single_room_category,
)
from normalizer_modules.activities import (
    _extract_supplier_day_heading,
    _is_group_tour_overview,
    looks_like_departure_text,
    normalize_activity_title,
)
from normalizer_modules.inclusions import normalize_inclusion_value, split_and_merge_inclusions
from normalizer_modules.times import expand_single_start_time_with_duration, normalize_time_range_fields
from normalizer_modules.transport import (
    _is_rail_or_fjord_route_activity,
    _is_route_transfer_activity,
    normalize_transport_title,
)


TRANSPORT_TYPES = {"Transport", "Train", "Flight", "Cruise", "Ferry"}












































def _looks_like_rental_vehicle_row(row: dict) -> bool:
    text = text_blob(row).lower()
    row_type = get_row_type(row).lower()
    if row_type == "car":
        return True
    return bool(re.search(r"\b(?:pick\s*up|pickup|deliver|return|drop(?:\s*off)?)\b.*\b(?:rental\s+car|car\s+rental|rental\s+vehicle)", text))


def _normalize_rental_vehicle_row(row: dict) -> dict:
    text = text_blob(row).lower()
    row["effective_type"] = "Car"
    row["type"] = "Car"
    if re.search(r"\b(?:deliver|return|drop(?:\s*off)?)\b", text):
        row["title"] = "Return your rental car"
    elif re.search(r"\b(?:pick\s*up|pickup)\b", text):
        row["title"] = "Pick up your rental car"
    else:
        row["title"] = "Rental car"
    row["original_title"] = row.get("original_title") or row.get("title")
    return row

def warn_suspicious_city(row: dict) -> None:
    city = clean_space(row.get("city", ""))
    if not city:
        return
    lower = city.lower()
    if is_likely_service_text(city) or any(marker in lower for marker in ["ticket", "option", "sightseeing", "private tour", "hop on", "hop-off", "cancel"]):
        diagnostics.warn(
            "suspicious_city",
            f"Suspicious city value '{city}' on {row.get('day', 'Unknown day')} — check source columns.",
            raw_value=row.get("raw", city),
        )
        row["city"] = ""
        return
    if city and not is_known_place(city) and len(city) > 18:
        diagnostics.warn(
            "unrecognised_city",
            f"City '{city}' on {row.get('day', 'Unknown day')} is not in the known place list — verify it is correct.",
            raw_value=row.get("raw", city),
        )





def normalize_row(row: dict) -> dict:
    row = copy.deepcopy(row)

    for key in ["city", "title", "original_title", "details", "meeting_point", "end_point", "luggage_included"]:
        if row.get(key):
            row[key] = polish_client_text(row[key])

    if row.get("duration"):
        duration_text = row["duration"]
        if re.search(r"\d+(?:\.\d+)?\s*(?:-|–|to)\s*\d+(?:\.\d+)?\s*hours?", duration_text, flags=re.IGNORECASE):
            row["duration"] = duration_text.replace("-", "–")
        else:
            row["duration"] = format_duration_display(duration_text)

    row["city"] = canonicalize_place_name(row.get("city", ""))
    warn_suspicious_city(row)

    row_type = get_row_type(row)
    full = text_blob(row)

    if looks_like_departure_text(full) and not _is_group_tour_overview(row):
        row["effective_type"] = "Departure"
        row["type"] = row.get("type") or "Departure"
        city = canonicalize_place_name(row.get("city", ""))
        row["title"] = f"Departure from {city}" if city else "Departure"
        return row

    if _looks_like_rental_vehicle_row(row):
        return _normalize_rental_vehicle_row(row)

    if row_type == "Hotel":
        return normalize_hotel_row(row)

    if row_type == "Activity":
        if _is_rail_or_fjord_route_activity(row):
            row["effective_type"] = "Train"
            if "norway in a nutshell" in full.lower():
                row["title"] = normalize_transport_title(row).get("title", row.get("title", ""))
            row_type = "Train"
        elif _is_route_transfer_activity(row):
            # Some sheets paste simple transport rows in the Activity column.
            # Preserve them as transport so they do not become guided experiences.
            if "flight" in full.lower():
                row["effective_type"] = "Flight"
                row_type = "Flight"
            elif "cruise" in full.lower() or "ferry" in full.lower():
                row["effective_type"] = "Cruise"
                row_type = "Cruise"
            elif "coach" in full.lower() or "bus" in full.lower():
                row["effective_type"] = "Transport"
                row_type = "Transport"
            elif "train" in full.lower():
                row["effective_type"] = "Train"
                row_type = "Train"
        if row_type == "Activity":
            title = normalize_activity_title(row)
            row["title"] = title
            row["original_title"] = row.get("original_title") or title
            if row.get("time"):
                row["display_time"] = expand_time_with_duration(row.get("time", ""), row.get("duration", ""))
            else:
                row["display_time"] = ""
            row["display_duration"] = format_duration_display(row.get("duration", "")) if row.get("duration") else ""

    if get_row_type(row) in TRANSPORT_TYPES or row_type == "Transfer":
        row = normalize_transport_title(row)

    if isinstance(row.get("includes"), list):
        row["includes"] = split_and_merge_inclusions(row.get("includes", []))
    if isinstance(row.get("notable_sights"), list):
        row["notable_sights"] = split_and_merge_inclusions(row.get("notable_sights", []))

    row = normalize_time_range_fields(row)
    return row


def add_repeated_activity_context(rows: list[dict]) -> list[dict]:
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
    for later in rows[current_index + 1:]:
        later_day = _day_number_value(later.get("day", ""))
        if later_day and current_day and later_day <= current_day:
            continue
        city = canonicalize_place_name(later.get("city", ""))
        if city and get_row_type(later) in {"Hotel", "Activity", "Transfer", "Transport", "Train", "Flight", "Cruise", "Ferry", "Departure"}:
            return city
    return ""


def apply_contextual_travel_corrections(rows: list[dict]) -> list[dict]:
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

    return updated

def _fill_missing_context_cities(rows: list[dict]) -> list[dict]:
    """Fill safe missing city values from nearby itinerary context.

    Some supplier sheets leave the city column empty on activity/hotel rows
    because the city is implied by the previous or same-day row. Filling these
    rows prevents summary chapters such as "Journey" and day headers with no
    city, while avoiding transport rows where multiple route cities may appear.
    """
    updated = [copy.deepcopy(row) for row in rows or []]
    city_by_day: dict[str, str] = {}

    preferred_types = {"Hotel", "Activity", "Arrival", "Departure", "Leisure"}
    for row in updated:
        city = canonicalize_place_name(row.get("city", ""))
        if city and get_row_type(row) in preferred_types and not is_likely_service_text(city) and city.lower() not in {"accommodation", "journey"}:
            city_by_day.setdefault(row.get("day", ""), city)

    previous_city = ""
    fillable_types = {"Hotel", "Activity", "Arrival", "Departure", "Leisure"}
    for row in updated:
        row_type = get_row_type(row)
        city = canonicalize_place_name(row.get("city", ""))
        if city and not is_likely_service_text(city) and city.lower() not in {"accommodation", "journey"}:
            previous_city = city
            continue
        if city.lower() in {"accommodation", "journey"}:
            row["city"] = ""
        if row_type in fillable_types:
            inferred = city_by_day.get(row.get("day", "")) or previous_city
            if inferred:
                row["city"] = inferred
                city_by_day.setdefault(row.get("day", ""), inferred)
                previous_city = inferred
    return updated


def normalize_itinerary_rows(rows: list[dict]) -> list[dict]:
    normalized = [normalize_row(row) for row in rows or []]
    normalized = _fill_missing_context_cities(normalized)
    normalized = apply_contextual_travel_corrections(normalized)
    normalized = add_repeated_activity_context(normalized)
    return normalized

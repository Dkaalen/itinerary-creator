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
    looks_like_leisure_activity,
    normalize_activity_title,
)
from normalizer_modules.inclusions import normalize_inclusion_value, split_and_merge_inclusions
from normalizer_modules.times import expand_single_start_time_with_duration, normalize_time_range_fields
from normalizer_modules.transport import (
    _is_rail_or_fjord_route_activity,
    _is_route_transfer_activity,
    normalize_transport_title,
)
from normalizer_modules.context import (
    _day_number_value,
    _next_main_city,
    add_repeated_activity_context,
    apply_contextual_travel_corrections,
    fill_missing_context_cities,
)
from itinerary_generation.transport_safety import repair_messy_client_text
from itinerary_generation.group_tours import annotate_group_tour_optional_extras
from normalizer_modules.rental import (
    looks_like_rental_vehicle_row,
    normalize_rental_vehicle_row,
)


TRANSPORT_TYPES = {"Transport", "Train", "Flight", "Cruise", "Ferry"}

# Compatibility aliases for older private imports. New code should import from
# normalizer_modules.context or normalizer_modules.rental directly.
_fill_missing_context_cities = fill_missing_context_cities
_looks_like_rental_vehicle_row = looks_like_rental_vehicle_row
_normalize_rental_vehicle_row = normalize_rental_vehicle_row


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
            row[key] = repair_messy_client_text(polish_client_text(row[key]))

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

    if looks_like_rental_vehicle_row(row):
        row = normalize_rental_vehicle_row(row)
        if isinstance(row.get("includes"), list):
            row["includes"] = split_and_merge_inclusions(row.get("includes", []))
        row = normalize_time_range_fields(row)
        return row

    if row_type == "Hotel":
        return normalize_hotel_row(row)

    if row_type == "Activity":
        if looks_like_leisure_activity(row):
            row["effective_type"] = "Leisure"
            row["type"] = row.get("type") or "Leisure"
            row["title"] = "Spend time at leisure"
            row["original_title"] = row.get("original_title") or row["title"]
            return row
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


def normalize_itinerary_rows(rows: list[dict]) -> list[dict]:
    normalized = [normalize_row(row) for row in rows or []]
    normalized = fill_missing_context_cities(normalized)
    normalized = apply_contextual_travel_corrections(normalized)
    normalized = add_repeated_activity_context(normalized)
    normalized = annotate_group_tour_optional_extras(normalized)
    return normalized

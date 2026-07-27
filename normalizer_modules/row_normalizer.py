"""Normalize one parsed itinerary row into client-safe domain data."""

import copy
import re

from itinerary_domain.nutshell_domain import attach_nutshell_journey, is_nutshell_row
from itinerary_domain.transport_norway import _is_norway_in_a_nutshell_text
from normalizer_modules.activities import (
    _is_group_tour_overview,
    looks_like_departure_text,
    looks_like_leisure_activity,
    normalize_activity_title,
)
from normalizer_modules.domain_enrichment import enrich_normalized_row_domain
from normalizer_modules.hotels import normalize_hotel_row
from normalizer_modules.inclusions import split_and_merge_inclusions
from normalizer_modules.rental import looks_like_rental_vehicle_row, normalize_rental_vehicle_row
from normalizer_modules.row_classification import looks_like_misclassified_hotel_row, warn_suspicious_city
from normalizer_modules.text_utils import get_row_type, text_blob
from normalizer_modules.times import normalize_time_range_fields
from normalizer_modules.transport_activity_detection import _is_rail_or_fjord_route_activity
from normalizer_modules.transport_title import normalize_transport_title
from normalizer_modules.transport_transfer_detection import _is_route_transfer_activity
from place_aliases import canonicalize_place_name
from shared.client_text_repair import repair_messy_client_text
from shared.source_text_cleanup import clean_supplier_source_text
from itinerary_domain.field_sanitation import CustomerField, sanitize_customer_field
from text_polish import expand_time_with_duration, format_duration_display

TRANSPORT_TYPES = {"Transport", "Train", "Flight", "Cruise", "Ferry"}


def protect_hotel_owned_text(value: str) -> str:
    return sanitize_customer_field(
        repair_messy_client_text(clean_supplier_source_text(value)),
        CustomerField.TITLE,
    )


_FIELD_TYPES = {
    "city": CustomerField.LOCATION,
    "title": CustomerField.TITLE,
    "original_title": CustomerField.TITLE,
    "details": CustomerField.DESCRIPTION,
    "meeting_point": CustomerField.MEETING_POINT,
    "end_point": CustomerField.LOCATION,
    "luggage_included": CustomerField.DESCRIPTION,
}


def _clean_base_fields(row, initial_type):
    del initial_type  # Field semantics, not source row type, own sanitation.
    for key, field in _FIELD_TYPES.items():
        if not row.get(key):
            continue
        source_safe = clean_supplier_source_text(row[key])
        row[key] = sanitize_customer_field(repair_messy_client_text(source_safe), field)

    if row.get("duration"):
        duration = row["duration"]
        if re.search(r"\d+(?:\.\d+)?\s*(?:-|–|to)\s*\d+(?:\.\d+)?\s*hours?", duration, re.I):
            row["duration"] = duration.replace("-", "–")
        else:
            row["duration"] = format_duration_display(duration)

    row["city"] = canonicalize_place_name(row.get("city", ""))
    warn_suspicious_city(row)


def _normalize_activity(row, row_type, full):
    if looks_like_leisure_activity(row):
        row.update(
            effective_type="Leisure",
            type=row.get("type") or "Leisure",
            title="Spend time at leisure",
            original_title=row.get("original_title") or "Spend time at leisure",
        )
        return row, "Leisure"

    if _is_rail_or_fjord_route_activity(row):
        row["effective_type"] = "Train"
        if _is_norway_in_a_nutshell_text(full):
            row["title"] = normalize_transport_title(row).get("title", row.get("title", ""))
        row_type = "Train"
    elif _is_route_transfer_activity(row):
        lower = full.lower()
        if "flight" in lower:
            row_type = "Flight"
        elif "cruise" in lower or "ferry" in lower:
            row_type = "Cruise"
        elif "coach" in lower or "bus" in lower:
            row_type = "Transport"
        elif "train" in lower:
            row_type = "Train"
        row["effective_type"] = row_type

    if row_type == "Activity":
        title = normalize_activity_title(row)
        row["title"] = title
        row["original_title"] = row.get("original_title") or title
        row["display_time"] = (
            expand_time_with_duration(row.get("time", ""), row.get("duration", "")) if row.get("time") else ""
        )
        row["display_duration"] = format_duration_display(row.get("duration", "")) if row.get("duration") else ""
    return row, row_type


def _normalize_lists(row):
    if isinstance(row.get("includes"), list):
        row["includes"] = split_and_merge_inclusions(row.get("includes", []))
        text = text_blob(row).lower()
        if get_row_type(row) == "Activity" and "icebreaker" in text and "cruise" in text:
            city = canonicalize_place_name(row.get("city", ""))
            items = [
                f"Shuttle bus from {city}" if city else "Shuttle bus transfer",
                "Icebreaker cruise",
                "Floating in icy Arctic waters in survival suits",
                "Walk on the frozen sea",
                "Complimentary hot drink",
                "Cruise & Swim certificate",
            ]
            row["includes"].extend(item for item in items if item not in row["includes"])
            row["includes"] = split_and_merge_inclusions(row["includes"])

    if isinstance(row.get("notable_sights"), list):
        row["notable_sights"] = split_and_merge_inclusions(row.get("notable_sights", []))
    return row


def _finalize_normalized_row(row: dict) -> dict:
    row = attach_nutshell_journey(row) if is_nutshell_row(row) else row
    row.pop("_normalization_source_title", None)
    return row


def normalize_row(row: dict) -> dict:
    row = copy.deepcopy(row)
    existing_product = row.get("activity_product")
    if isinstance(existing_product, dict) and existing_product.get("source_title"):
        row["_normalization_source_title"] = str(existing_product["source_title"])
    initial = get_row_type(row)
    row_type = enrich_normalized_row_domain(row)
    _clean_base_fields(row, initial)
    full = text_blob(row)

    if looks_like_misclassified_hotel_row(row):
        row["effective_type"] = "Hotel"
        row["type"] = row.get("type") or "Hotel"
        return _finalize_normalized_row(normalize_hotel_row(row))

    if looks_like_departure_text(full) and not _is_group_tour_overview(row):
        row["effective_type"] = "Departure"
        row["type"] = row.get("type") or "Departure"
        city = canonicalize_place_name(row.get("city", ""))
        row["title"] = f"Departure from {city}" if city else "Departure"
        return _finalize_normalized_row(row)

    if looks_like_rental_vehicle_row(row):
        row = normalize_rental_vehicle_row(row)
        if isinstance(row.get("includes"), list):
            row["includes"] = split_and_merge_inclusions(row.get("includes", []))
        return _finalize_normalized_row(normalize_time_range_fields(row))

    if row_type == "Hotel":
        return _finalize_normalized_row(normalize_hotel_row(row))

    if row_type == "Activity":
        row, row_type = _normalize_activity(row, row_type, full)
        if row_type == "Leisure":
            return _finalize_normalized_row(row)

    if get_row_type(row) in TRANSPORT_TYPES or row_type == "Transfer":
        row = normalize_transport_title(row)

    row = normalize_time_range_fields(_normalize_lists(row))
    return _finalize_normalized_row(row)

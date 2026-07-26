"""Field-preserving source-row text standardization.

This stage runs after semantic row classification and source-route extraction,
but before type-specific normalization.  It preserves the established parser →
normalizer output while keeping client-facing transport-title decisions outside
raw parsing.
"""

from __future__ import annotations

import re

from itinerary_generation.transport_domain.parser import (
    create_clean_transport_title,
    standardize_private_transfer_title,
    standardize_self_transfer_title,
    standardize_shuttle_transfer_title,
)
from shared.source_text_cleanup import fix_common_text
from shared.source_time import normalize_duration_text, normalize_time_text
from text_polish_modules.text_cleanup import polish_hotel_name


def _fix_common_text_for_context(value: object, *, row_type: str = "", field: str = "") -> str:
    """Clean one source field while preserving supplier-owned hotel names."""

    if row_type == "Hotel" and field in {"title", "details", "hotel_name"}:
        protected = re.sub(r"\bAurora\b", "__HOTEL_AURORA__", str(value or ""), flags=re.IGNORECASE)
        cleaned = fix_common_text(protected)
        restored = cleaned.replace("__HOTEL_AURORA__", "Aurora")
        return polish_hotel_name(restored) if field in {"title", "hotel_name"} else restored
    return fix_common_text(value)


def standardize_source_row_text(row: dict) -> dict:
    """Apply legacy-safe text cleanup after semantic classification."""

    row_type = row.get("effective_type") or row.get("type", "")
    for key in (
        "city",
        "title",
        "details",
        "meeting_point",
        "end_point",
        "luggage_included",
        "hotel_name",
        "room_category",
        "meal_plan",
    ):
        if key in row and row.get(key):
            row[key] = _fix_common_text_for_context(row[key], row_type=row_type, field=key)

    if row.get("time"):
        row["time"] = normalize_time_text(row["time"])
    if row.get("duration"):
        row["duration"] = normalize_duration_text(row["duration"])

    for key in ("notable_sights", "includes"):
        if key in row and isinstance(row.get(key), list):
            cleaned_items = []
            for item in row[key]:
                cleaned = fix_common_text(item)
                cleaned = normalize_time_text(cleaned) or cleaned
                if cleaned:
                    cleaned_items.append(cleaned)
            row[key] = cleaned_items

    title = row.get("title", "")
    details = row.get("details", "")
    city = row.get("city", "")
    combined_lower = f"{title} {details}".lower()

    transfer_source_title = str(row.get("original_title") or title)
    transfer_lower = f"{transfer_source_title} {details}".lower()
    if row_type == "Transfer":
        if "self transfer" in transfer_lower or "self-transfer" in transfer_lower:
            row["title"] = standardize_self_transfer_title(transfer_source_title, details, city)
        elif "private" in transfer_lower:
            row["title"] = standardize_private_transfer_title(transfer_source_title, details, city)
        elif "shuttle" in transfer_lower:
            row["title"] = standardize_shuttle_transfer_title(transfer_source_title, details, city)
        elif re.search(r"\b(?:train|coach|bus|flight|cruise|ferry)\b", transfer_lower):
            source_row = dict(row)
            source_row["title"] = transfer_source_title
            row["title"] = create_clean_transport_title(source_row)

    if row_type in {"Arrival", "Departure"} and any(
        marker in combined_lower for marker in ("private", "shuttle", "self transfer", "self-transfer")
    ):
        if "self transfer" in combined_lower or "self-transfer" in combined_lower:
            row["title"] = standardize_self_transfer_title(title, details, city)
        elif "private" in combined_lower:
            row["title"] = standardize_private_transfer_title(title, details, city)
        elif "shuttle" in combined_lower:
            row["title"] = standardize_shuttle_transfer_title(title, details, city)

    if row_type in {"Transport", "Train", "Flight", "Cruise", "Ferry"}:
        row["title"] = create_clean_transport_title(row)

    return row


__all__ = ["standardize_source_row_text"]

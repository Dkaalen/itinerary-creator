"""Client-facing parser row text standardization."""
import re

from place_aliases import is_known_place

from parser_modules.common import *  # noqa: F401,F403
from parser_modules.time_parsing import normalize_duration_text, normalize_time_text

def _fix_common_text_for_context(value, *, row_type="", field=""):
    """Run parser cleanup while preserving supplier-owned hotel text."""

    if row_type == "Hotel" and field in {"title", "details", "hotel_name"}:
        protected = re.sub(r"\bAurora\b", "__HOTEL_AURORA__", str(value or ""), flags=re.IGNORECASE)
        cleaned = fix_common_text(protected)
        return polish_hotel_name(cleaned.replace("__HOTEL_AURORA__", "Aurora")) if field in {"title", "hotel_name"} else cleaned.replace("__HOTEL_AURORA__", "Aurora")
    return fix_common_text(value)

def standardize_row_text(row):
    """Applies client-facing cleanup after row parsing and effective type detection."""

    # Do not run the broad client-text polish on parsed time values.
    # Time fields are normalized by the dedicated time parser; broad punctuation
    # polish can corrupt clock syntax if it ever changes colon spacing.
    row_type = row.get("effective_type") or row.get("type", "")
    for key in ["city", "title", "details", "meeting_point", "end_point", "luggage_included", "hotel_name", "room_category", "meal_plan"]:
        if key in row and row.get(key):
            row[key] = _fix_common_text_for_context(row[key], row_type=row_type, field=key)

    if row.get("time"):
        row["time"] = normalize_time_text(row["time"])
    if row.get("duration"):
        row["duration"] = normalize_duration_text(row["duration"])

    for key in ["notable_sights", "includes"]:
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

    if row_type == "Transfer":
        if "self transfer" in combined_lower or "self-transfer" in combined_lower:
            row["title"] = standardize_self_transfer_title(title, details, city)
        elif "private" in combined_lower:
            row["title"] = standardize_private_transfer_title(title, details, city)
        elif "shuttle" in combined_lower:
            row["title"] = standardize_shuttle_transfer_title(title, details, city)
        elif re.search(r"\b(?:train|coach|bus|flight|cruise|ferry)\b", combined_lower):
            row["title"] = create_clean_transport_title(row)

    if row_type in {"Arrival", "Departure"} and any(marker in combined_lower for marker in ["private", "shuttle", "self transfer", "self-transfer"]):
        if "self transfer" in combined_lower or "self-transfer" in combined_lower:
            row["title"] = standardize_self_transfer_title(title, details, city)
        elif "private" in combined_lower:
            row["title"] = standardize_private_transfer_title(title, details, city)
        elif "shuttle" in combined_lower:
            row["title"] = standardize_shuttle_transfer_title(title, details, city)

    if row_type in {"Transport", "Train", "Flight", "Cruise", "Ferry"}:
        row["title"] = create_clean_transport_title(row)

    return row

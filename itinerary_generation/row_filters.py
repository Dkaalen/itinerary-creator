"""Row type and inclusion filters for itinerary generation."""

from __future__ import annotations


def get_row_type(row):
    return row.get("effective_type") or row.get("type", "")


def add_unique(items, item):
    clean_item = str(item or "").strip()

    if clean_item and clean_item not in items:
        items.append(clean_item)


def is_optional_row(row):
    return bool(row.get("is_optional"))


def main_rows_only(rows):
    return [row for row in rows if not is_optional_row(row)]


def optional_rows_only(rows):
    return [row for row in rows if is_optional_row(row)]


def get_activity_text(row):
    return f'{row.get("original_title", "")} {row.get("title", "")} {row.get("details", "")}'.lower()


def has_hotel(day_rows):
    return any(get_row_type(row) == "Hotel" for row in day_rows)


def has_self_drive_markers(parsed_rows):
    """Detect true rental-car/self-drive itinerary patterns.

    Do not treat ordinary self transfers, coach routes, supplier prose like
    "we drive", or scenic/return-drive day descriptions as self-drive. The
    itinerary should only be labelled self-drive when a rental vehicle/car is
    explicitly part of the arranged journey.
    """
    positive_markers = [
        "rental vehicle", "rental car", "rental suv", "pick up rental",
        "pickup rental", "drop vehicle", "drop off vehicle", "return vehicle",
        "car rental", "hire car",
    ]
    negative_markers = [
        "self transfer", "self-arranged", "self arranged", "coach", "bus",
        "flight", "train", "cruise", "ferry", "private transfer",
    ]
    for row in parsed_rows or []:
        text = f'{row.get("type", "")} {row.get("title", "")} {row.get("details", "")} {row.get("original_title", "")}'.lower()
        if any(marker in text for marker in positive_markers) and not ("self transfer" in text and "rental" not in text):
            return True
    return False


def is_self_arranged(row):
    text = f'{row.get("title", "")} {row.get("details", "")}'.lower()
    row_type = get_row_type(row)

    # Activity descriptions often contain exclusions like "guide not included"
    # or "food and drinks not included". Those should not turn the whole
    # experience into self-arranged travel.
    if row_type == "Activity":
        return False

    markers = [
        "self arranged",
        "self-arranged",
        "self arrnaged",
        "cost not included",
        "cost not inclueded",
        "price not included",
        "flight cost not",
    ]

    return any(marker in text for marker in markers)

"""Rental vehicle normalization helpers."""

from __future__ import annotations

import re

from normalizer_modules.text_utils import clean_space, get_row_type, text_blob


_RENTAL_ROW_RE = re.compile(
    r"\b(?:pick\s*up\s+(?:your\s+)?rental|pickup\s+rental|rental\s+(?:vehicle|car|suv)|car\s+rental|hire\s+car|deliver\s+(?:your\s+)?rental|return\s+(?:your\s+)?rental|drop\s*(?:off)?\s+(?:your\s+)?rental)\b",
    flags=re.IGNORECASE,
)


def looks_like_rental_vehicle_row(row: dict) -> bool:
    row_type = get_row_type(row)
    text = text_blob(row)
    if row_type == "Car":
        return True
    # Some supplier sheets incorrectly put rental-car return rows in the Hotel
    # column. Correct those rows before accommodation normalization, but leave
    # Day Overview rental blocks alone because the overview renderer already
    # has specific client-facing rental wording.
    if row_type == "Hotel" and _RENTAL_ROW_RE.search(text):
        return True
    return False


def normalize_rental_vehicle_row(row: dict) -> dict:
    text = text_blob(row)
    lower = text.lower()
    row["type"] = "Car"
    row["effective_type"] = "Car"
    if re.search(r"\b(?:deliver|return|drop\s*(?:off)?)\b", lower):
        row["title"] = "Rental car return"
    elif re.search(r"\b(?:pick\s*up|pickup)\b", lower):
        row["title"] = "Rental car pick-up"
    elif not clean_space(row.get("title", "")):
        row["title"] = "Rental vehicle"
    return row

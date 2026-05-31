"""Parser row type/date/day detection helpers."""

import re

from .text_cleanup import clean_space

DETAIL_LABELS = [
    "Time",
    "Meeting point",
    "End point",
    "Includes",
    "Notable Sights",
    "Schedule",
    "Description",
    "Overview",
    "Luggage included",
]

DETAIL_MARKERS = [f" - {label}:" for label in DETAIL_LABELS]
DAY_PATTERN = re.compile(r"^day\s+\d+", re.IGNORECASE)
DATE_PATTERN = re.compile(r"^\d{1,2}[./-]\d{1,2}[./-]\d{2,4}$")
KNOWN_TYPES = {
    "arrival",
    "transfer",
    "transport",
    "hotel",
    "activity",
    "leisure",
    "departure",
    "train",
    "flight",
    "cruise",
    "ferry",
    "car",
    "drive",
}


def normalize_type(value):
    return clean_space(value).title()


def looks_like_day(value):
    return bool(DAY_PATTERN.match(clean_space(value)))


def looks_like_date(value):
    return bool(DATE_PATTERN.match(clean_space(value)))


def looks_like_known_type(value):
    return clean_space(value).lower() in KNOWN_TYPES


def is_optional_addon_header(value):
    text = clean_space(value).lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = clean_space(text)
    # Supplier sheets contain many typo variants: optional addon, optinal addon,
    # optional add-on, addon on request. Treat all as optional commercial items.
    has_optional = "optional" in text or "optinal" in text or "on request" in text
    has_addon = any(marker in text for marker in ["addon", "add on", "addons", "add ons", "add on request", "addon on request"])
    return has_optional and (has_addon or "on request" in text)

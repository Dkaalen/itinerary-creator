"""Parser row type/date/day detection helpers."""

import re

from .text_cleanup import clean_space

DETAIL_LABELS = [
    "Time",
    "Meeting point",
    "End point",
    "Includes",
    "Included",
    "Excludes",
    "Not included",
    "Notable Sights",
    "Highlights",
    "Stops",
    "Schedule",
    "Description",
    "Overview",
    "What to expect",
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
    "optional",
    "day overview",
    "group tour",
    "activity upgrade",
    "transfer package",
    "single supplement fee",
    "extra hotel night",
}


def normalize_type(value):
    return clean_space(value).title()


def looks_like_day(value):
    return bool(DAY_PATTERN.match(clean_space(value)))


def looks_like_date(value):
    return bool(DATE_PATTERN.match(clean_space(value)))


def looks_like_known_type(value):
    return clean_space(value).lower() in KNOWN_TYPES


def _normalized_optional_text(value):
    text = clean_space(value).lower()
    text = re.sub(r"[^a-z0-9/ ]+", " ", text)
    return clean_space(text)


def is_optional_addon_header(value):
    """Return True only for explicit optional-section/add-on headers.

    This intentionally does *not* treat generic supplier prose such as
    "other languages available on request" as optional. Optional status is a
    commercial row state and must not leak from descriptive text into the main
    itinerary structure.
    """
    text = _normalized_optional_text(value)
    if not text:
        return False

    # Standalone section headings pasted above rows. Do not match generic
    # "Optional:" bullet labels inside day-overview prose or supplier
    # descriptions; those belong to the current row, not to later rows.
    section_headings = {
        "optional add ons",
        "optional addons",
        "optional add on",
        "optional addon",
        "optional experiences",
        "optional extras",
        "add ons",
        "addons",
    }
    return text in section_headings


def is_explicit_optional_text(value):
    """Return True when a row itself clearly declares optional status."""
    text = _normalized_optional_text(value)
    optional_prefixes = (
        "optional",
        "optinal",
        "optional/recommended",
        "optional recommended",
        "optional recommeded",
        "available as optional",
        "addon optional",
        "add on optional",
        "add on activity optional",
    )
    if text.startswith(optional_prefixes):
        return True
    return bool(re.match(r"^(?:addon|add on)\s+optional\s+(?:activity\s+)?(?:at\s+addi?t?ional\s+cost|on\s+request)\b", text))

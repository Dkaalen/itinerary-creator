"""Parser row type/date/day detection helpers."""

import re

from shared.text import clean_space
from shared.row_type_values import (
    DATE_PATTERN,
    DAY_PATTERN,
    KNOWN_TYPES,
    TYPE_ALIASES,
    looks_like_date,
    looks_like_day,
    looks_like_known_type,
    normalize_type,
)

DETAIL_LABELS = [
    "Time",
    "Driving time",
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
_NON_ITINERARY_TYPE_PATTERNS = (
    r"^per\s+pax$",
    r"^one\s+pax$",
    r"^single\s+room\s+cost$",
    r"^total$",
    r"^subtotal$",
    r"^sub\s+total$",
    r"^margin$",
    r"^gross$",
    r"^net$",
    r"^adult$",
    r"^child$",
    r"^\d+(?:\.\d+)?$",
)


def looks_like_non_itinerary_type(value):
    """Return True for calculator/costing rows that should not become itinerary rows."""

    text = clean_space(value).lower().strip(" :,-")
    if not text:
        return False
    if looks_like_day(text) or looks_like_date(text):
        return True
    return any(re.match(pattern, text) for pattern in _NON_ITINERARY_TYPE_PATTERNS)


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

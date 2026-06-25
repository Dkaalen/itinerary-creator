"""Constants for Vipin Excel corpus extraction/evaluation."""

from __future__ import annotations

import re

MAIN_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"

HEADER_ALIASES = {
    "day": {"day"},
    "type": {"type"},
    "city": {"city", "city / area", "location", "destination"},
    "element": {"travel element", "details", "activity", "description"},
    "nights": {"no of night", "no of nights", "nights"},
    "from_date": {"from date", "date"},
    "to_date": {"to date"},
    "supplier": {"supplier"},
}

NON_ITINERARY_TYPES = {
    "",
    "per pax",
    "one pax",
    "two pax",
    "three pax",
    "four pax",
    "five pax",
    "six pax",
    "price",
    "cost",
    "total",
    "margin",
    "markup",
}

ALLOWED_EMPTY_TITLE_TYPES = {"Arrival", "Departure", "Leisure"}
TITLE_PROSE_MARKERS = re.compile(
    r"\b(overview|what'?s included|what is included|meeting point|pick[- ]?up / meeting|pick[- ]?up point|"
    r"end point|notable sights|highlights:|duration:|includes?:|important information|please note|"
    r"the full arctic expedition|professional[, ]+english[- ]speaking|client will|you will)\b",
    flags=re.IGNORECASE,
)
DAY_RE = re.compile(r"\bday\s*\d+\b", flags=re.IGNORECASE)
DATEISH_RE = re.compile(r"\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?|\d{4}-\d{2}-\d{2}")

"""Neutral normalization of source row-type labels.

This module owns lexical row-type normalization shared by raw parsing and
semantic enrichment.  It deliberately contains no source classification or
route inference.
"""

from __future__ import annotations

import re

from shared.text import clean_space


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
    "notes",
    "activity upgrade",
    "actvity upgrade",
    "transfer package",
    "single supplement fee",
    "extra hotel night",
    "extra day",
}

TYPE_ALIASES = {
    "actvity upgrade": "Activity Upgrade",
    "activity upgrde": "Activity Upgrade",
    "activty upgrade": "Activity Upgrade",
    "bus": "Transport",
    "coach": "Transport",
    "criuse": "Cruise",
    "cruies": "Cruise",
    "cruize": "Cruise",
    "ferrry": "Ferry",
    "fery": "Ferry",
}


def normalize_type(value: object) -> str:
    """Return the canonical display label for a lexical source type value."""

    text = clean_space(value)
    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    return TYPE_ALIASES.get(normalized, text.title())


def looks_like_day(value: object) -> bool:
    return bool(DAY_PATTERN.match(clean_space(value)))


def looks_like_date(value: object) -> bool:
    return bool(DATE_PATTERN.match(clean_space(value)))


def looks_like_known_type(value: object) -> bool:
    return normalize_type(value).lower() in KNOWN_TYPES


__all__ = [
    "DATE_PATTERN",
    "DAY_PATTERN",
    "KNOWN_TYPES",
    "TYPE_ALIASES",
    "looks_like_date",
    "looks_like_day",
    "looks_like_known_type",
    "normalize_type",
]

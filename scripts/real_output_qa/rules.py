"""Deterministic rule constants for real-output text scoring."""

from __future__ import annotations

import re

from shared.text_cleanup_rules import SUPPLIER_TYPO_PATTERNS

CURRENCY_CODES = frozenset({"DKK", "EUR", "GBP", "ISK", "NOK", "SEK", "USD"})

SUSPICIOUS_PHRASES: tuple[str, ...] = (
    "unhurried",
    "the day’s arrangements are listed below",
    "the day's arrangements are listed below",
    "planned experience in",
    "key arrangements prepared in advance",
    "wider day kept easy to follow",
)

ROUTE_FALSE_PLACE_RE = re.compile(
    r"\b(?:activity upgrade|actvity upgrade|shuttle transfer|self transfer|transfer package|airport transfer)\b",
    flags=re.IGNORECASE,
)
AIRPORT_STAY_RE = re.compile(r"\b(?:airport|terminal)\b", flags=re.IGNORECASE)
RAW_SUPPLIER_FRAGMENT_RE = re.compile(
    r"\s-\s(?:Time|Meeting point|End point|Duration|Departure from|Departing from|Arrival|Start time):",
    flags=re.IGNORECASE,
)
TRANSFER_AS_PLACE_RE = re.compile(
    r"\b(?:travel|transfer|shuttle transfer)\s+from\s+(?:shuttle transfer|self transfer)\b",
    flags=re.IGNORECASE,
)
TRANSPORT_PRODUCT_RE = re.compile(
    r"\b(?:coach|bus|shuttle|transfer|train|flight|ferry|cruise transfer|airport transfer|arctic route)\b",
    flags=re.IGNORECASE,
)
ACTIVITY_TRANSPORT_EXPERIENCE_RE = re.compile(
    r"\b(?:northern lights|aurora|hunt|safari|sightseeing|tour|excursion|guided|fjord|cruise|reindeer|husky|whale|hike|experience)\b",
    flags=re.IGNORECASE,
)
GENERIC_COPY_RE = re.compile(
    r"\b(?:planned experience|arrangements are listed below|key arrangements prepared in advance|wider day kept easy to follow)\b",
    flags=re.IGNORECASE,
)
ACTIVITY_TYPE_RE = re.compile(r"\bactivity\b", flags=re.IGNORECASE)

__all__ = [
    "ACTIVITY_TRANSPORT_EXPERIENCE_RE",
    "ACTIVITY_TYPE_RE",
    "AIRPORT_STAY_RE",
    "CURRENCY_CODES",
    "GENERIC_COPY_RE",
    "RAW_SUPPLIER_FRAGMENT_RE",
    "ROUTE_FALSE_PLACE_RE",
    "SUPPLIER_TYPO_PATTERNS",
    "SUSPICIOUS_PHRASES",
    "TRANSFER_AS_PLACE_RE",
    "TRANSPORT_PRODUCT_RE",
]

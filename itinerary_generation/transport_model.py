"""Shared transport-row model helpers.

Transport wording is used by day pages, final inclusions, exclusions and
validation. Keep low-level row/source interpretation here so those layers do
not each rebuild slightly different ideas of what a transport row is.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from itinerary_generation.common import TRANSPORT_TYPES, get_row_type


TRANSPORT_CORE_FIELDS: tuple[str, ...] = ("title", "details")
TRANSPORT_SOURCE_FIELDS: tuple[str, ...] = (*TRANSPORT_CORE_FIELDS, "original_title")

# Markers that describe point-to-point/local logistics rather than route
# transport. These should not be treated as route transfers even when they
# contain words such as "to" or a valid destination city.
LOCAL_TRANSFER_MARKERS: tuple[str, ...] = (
    "private",
    "shuttle",
    "self transfer",
    "hotel to",
    "airport to",
    "to hotel",
    "to airport",
    "to station",
    "to your accommodation",
    "accommodation",
)


@dataclass(frozen=True)
class TransportRowContext:
    """Small immutable view of transport-relevant row state."""

    row_type: str
    source_text: str
    search_text: str


def get_transport_source_text(row: dict, fields: Iterable[str] = TRANSPORT_SOURCE_FIELDS) -> str:
    """Return the combined supplier text used by transport extractors.

    The parser may place route, schedule or cabin details in different fields
    depending on input format. This helper keeps the source-field priority
    consistent across route, title, time and inclusion extraction.
    """

    return " ".join(
        str(row.get(key, "") or "")
        for key in fields
        if str(row.get(key, "") or "").strip()
    )


def get_transport_search_text(row: dict) -> str:
    """Return lower-case transport source text for marker checks."""

    return get_transport_source_text(row).lower()


def get_transport_row_context(row: dict) -> TransportRowContext:
    """Return the shared transport context for a parsed row."""

    row_type = get_row_type(row)
    source_text = get_transport_source_text(row)
    return TransportRowContext(row_type=row_type, source_text=source_text, search_text=source_text.lower())


def has_local_transfer_marker(text: str) -> bool:
    """True when text describes local/private/self-transfer logistics."""

    lower = str(text or "").lower()
    return any(marker in lower for marker in LOCAL_TRANSFER_MARKERS)


def is_transport_like_row(row: dict, *, include_drive: bool = False) -> bool:
    """Return whether a row participates in travel-arrangement rendering."""

    row_type = get_row_type(row)
    return row_type == "Transfer" or row_type in TRANSPORT_TYPES or (include_drive and row_type == "Drive")

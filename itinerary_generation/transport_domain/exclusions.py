"""Transport-specific commercial exclusion helpers."""

from __future__ import annotations

import re

from text_polish import polish_title

from itinerary_generation.common import TRANSPORT_TYPES, get_row_type
from itinerary_generation.transport_domain.titles import get_transport_route_phrase, get_transfer_travel_title
from itinerary_generation.transport_safety import clean_self_transfer_text, split_self_transfer_notes

TRANSPORT_ROW_TYPES = set(TRANSPORT_TYPES) | {"Transfer", "Transport", "Train", "Flight", "Cruise", "Ferry", "Drive"}


def row_search_text(row: dict) -> str:
    return " ".join(
        str(row.get(key, "") or "")
        for key in ["source_type", "type", "effective_type", "title", "original_title", "details"]
    ).lower().replace("-", " ")


def is_self_transfer_row(row: dict) -> bool:
    return "self transfer" in row_search_text(row)


def is_flight_row(row: dict) -> bool:
    return get_row_type(row) == "Flight" or "flight" in row_search_text(row)


def is_transport_row(row: dict) -> bool:
    text = row_search_text(row)
    return get_row_type(row) in TRANSPORT_ROW_TYPES or any(
        marker in text
        for marker in ["transfer", "flight", "train", "coach", "bus", "ferry", "cruise", "shuttle"]
    )


def self_arranged_flight_notice(row: dict) -> str:
    """Return a clear commercial exclusion label for a self-arranged flight."""

    destination = ""
    origin = ""
    text = " ".join(str(row.get(key, "") or "") for key in ["details", "original_title", "title"])
    route_match = re.search(
        r"\bflight\s+(?:from\s+)?(?P<origin>[A-ZÀ-ÝÆØÅÄÖ][A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{1,35}?)\s+to\s+(?P<destination>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)(?:\s*,|\s+-|\s*\||\s+self\b|\s+cost\b|$)",
        text,
        flags=re.IGNORECASE,
    )
    if route_match:
        origin = polish_title(route_match.group("origin").strip(" -:|.,"))
        destination = polish_title(route_match.group("destination").strip(" -:|.,"))
        # Unit title-only notices historically omit the origin; itinerary rows
        # with a known source city keep it for clearer route context.
        if not str(row.get("city") or "").strip():
            origin = ""
    if not destination:
        title = str(row.get("title") or "")
        match = re.search(r"\bflight\s+to\s+(.+)$", title, flags=re.IGNORECASE)
        if match:
            destination = polish_title(match.group(1).strip(" -:|.,"))
    if not origin and destination:
        origin = polish_title(str(row.get("city") or "").strip(" -:|.,"))
    if origin and destination:
        return f"Self-arranged flight from {origin} to {destination} (not included)"
    if destination:
        return f"Self-arranged flight to {destination} (not included)"
    return "Self-arranged flight (not included)"


def self_transfer_exclusion_title(row: dict) -> str:
    """Return the first clean self-transfer exclusion title for a row."""

    source = row.get("details") or row.get("title") or row.get("original_title")
    notes = split_self_transfer_notes(source)
    if notes:
        return notes[0][:140].strip(" -:|")
    return clean_self_transfer_text(source)[:140].strip(" -:|")


def transport_commercial_title(row: dict) -> str:
    """Return client-facing title for transport rows in exclusions."""

    if is_self_transfer_row(row):
        return self_transfer_exclusion_title(row)
    if get_row_type(row) in set(TRANSPORT_TYPES) | {"Transfer"}:
        return (get_transport_route_phrase(row) or get_transfer_travel_title(row) or "")[:120].strip(" -:|")
    return ""

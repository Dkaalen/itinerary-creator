"""Parser row confidence and review flags.

These helpers annotate parsed supplier rows with lightweight signals used by the
structured input review.  They do not block generation; they make uncertain
hotel/transport/activity extraction visible before polishing or PDF export.
"""

from __future__ import annotations

from typing import Any, Mapping

from parser_modules.place_parsing import extract_route_points
from parser_modules.type_detection import normalize_type

_IMPORTANT_CITY_TYPES = {"Hotel", "Activity", "Transfer", "Transport", "Train", "Flight", "Cruise", "Ferry"}
_ROUTE_TYPES = {"Transfer", "Transport", "Train", "Flight", "Cruise", "Ferry"}


def _text(row: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = str(row.get(key, "") or "").strip()
        if value:
            return value
    return ""


def _is_sparse_route_summary(row: Mapping[str, Any]) -> bool:
    text = _text(row, "title", "original_title", "details", "description").lower()
    if text in {"arrival", "departure", "rental car", "airport"}:
        return True
    if text.startswith("arrival in ") or text.startswith("departure from "):
        return True
    if text in {"reykjavík", "reykjavik"}:
        return True
    return False


def _combined_text(row: Mapping[str, Any]) -> str:
    return " ".join(
        value for value in (_text(row, key) for key in ("title", "original_title", "details", "description")) if value
    ).lower()


def _is_local_route_without_points(row: Mapping[str, Any]) -> bool:
    text = _combined_text(row)
    if not text:
        return False
    local_markers = (
        "transfer in ",
        "leisure day",
        "no services",
        "standard pricing applies",
        "pick-up rental car",
        "rental car",
        "drop your vehicle",
        "self-arranged local transfer",
        "suggested local transfer",
        "round trip tallinn ferry",
        "round trip tallin ferry",
        "city tour ends",
        "walking distance",
        "vehicle category",
        "flight self-arranged",
        "flight self arranged",
        "flight to ",
        "cost not included",
        "cost on included",
        "next day arrival in",
        "overnight cruise",
        "optional addon",
        "shuttle bus from",
    )
    if any(marker in text for marker in local_markers):
        return True
    if "private transfer" in text and any(marker in text for marker in (" to hotel", " to your accommodation", " from the airport", " from airport", " from hotel")):
        return True
    if "self" in text and "transfer" in text and any(marker in text for marker in ("meeting point", "central station", "hotel to", "airport to")):
        return True
    if ("hotel" in text or "xnight" in text or "x night" in text or "breakfast" in text or "standard room" in text) and not any(marker in text for marker in ("flight", "train", "bus", "coach", "ferry", "cruise")):
        return True
    return False


def _is_sparse_hotel_summary(row: Mapping[str, Any]) -> bool:
    text = _combined_text(row)
    if not text:
        return False
    hotel_name = _text(row, "hotel_name", "hotel", "accommodation").lower()
    room_markers = ("room", "cabin", "cabinn", "suite", "igloo", "apartment", "studio", "bed")
    short_name_only = len(text.split()) <= 7 and not any(marker in text for marker in room_markers)
    return (
        "self-arranged" in text
        or "self arranged" in text
        or hotel_name.startswith("accommodation in ")
        or "private transfer to your accommodation" in text
        or text in {"hotel", "stockholm", "reykjavík", "reykjavik", "grindavík", "grindavik"}
        or text.startswith("stay at ")
        or "challet/ villa" in text
        or short_name_only
    )


def _route_points(row: Mapping[str, Any]) -> tuple[str, str]:
    origin = _text(row, "route_origin", "origin", "from", "from_city")
    destination = _text(row, "route_destination", "destination", "to", "to_city")
    if origin and destination:
        return origin, destination
    extracted_origin, extracted_destination = extract_route_points(" ".join(
        _text(row, key) for key in ("title", "details", "description", "original_title") if _text(row, key)
    ))
    return origin or extracted_origin, destination or extracted_destination


def parser_review_flags(row: Mapping[str, Any]) -> tuple[str, ...]:
    """Return deterministic review flags for one parsed row."""

    row_type = normalize_type(_text(row, "effective_type", "type"))
    flags: list[str] = []
    title = _text(row, "title", "original_title", "hotel_name", "name")
    details = _text(row, "details", "description")
    city = _text(row, "city", "destination", "location")

    sparse_route_summary = row_type in _ROUTE_TYPES and _is_sparse_route_summary(row)
    local_route_without_points = row_type in _ROUTE_TYPES and _is_local_route_without_points(row)
    origin, destination = _route_points(row) if row_type in _ROUTE_TYPES and not sparse_route_summary and not local_route_without_points else ("", "")
    if row_type in _IMPORTANT_CITY_TYPES and not city and not sparse_route_summary and not local_route_without_points and not (row_type in _ROUTE_TYPES and destination):
        flags.append("missing_city")
    if row_type == "Hotel":
        sparse_hotel_summary = _is_sparse_hotel_summary(row)
        if not _text(row, "hotel_name", "hotel", "accommodation"):
            flags.append("missing_hotel_name")
        if not sparse_hotel_summary and not _text(row, "hotel_nights", "nights"):
            flags.append("missing_hotel_nights")
        if not sparse_hotel_summary and not _text(row, "room_category", "room"):
            flags.append("missing_room_category")
    if row_type in _ROUTE_TYPES and not sparse_route_summary and not local_route_without_points:
        if not origin:
            flags.append("missing_route_origin")
        if not destination:
            flags.append("missing_route_destination")
    if row_type == "Activity" and not title:
        flags.append("missing_activity_title")
    if title and len(title) < 4 and row_type not in {"Arrival", "Departure"}:
        flags.append("weak_title")
    if details and len(details) > 1800:
        flags.append("very_long_supplier_text")

    seen: set[str] = set()
    unique: list[str] = []
    for flag in flags:
        if flag not in seen:
            seen.add(flag)
            unique.append(flag)
    return tuple(unique)


def parser_confidence(row: Mapping[str, Any]) -> int:
    """Return a 0-100 row confidence score based on review flags."""

    flags = parser_review_flags(row)
    score = 100
    weights = {
        "missing_hotel_name": 45,
        "missing_route_destination": 35,
        "missing_route_origin": 25,
        "missing_city": 20,
        "missing_activity_title": 30,
        "missing_hotel_nights": 15,
        "missing_room_category": 10,
        "weak_title": 10,
        "very_long_supplier_text": 10,
    }
    for flag in flags:
        score -= weights.get(flag, 8)
    return max(0, min(100, score))


def annotate_parser_quality(row: dict[str, Any]) -> dict[str, Any]:
    """Attach parser confidence metadata to a mutable row and return it."""

    flags = parser_review_flags(row)
    row["parser_review_flags"] = list(flags)
    row["parser_confidence"] = parser_confidence(row)
    return row

"""Row, route and day-level facts used by itinerary health checks."""

import re
from typing import Any, Iterable, Mapping

from itinerary_generation.health_check_models import CONTENT_TYPES, TRANSFER_TYPES
from itinerary_generation.row_filters import get_row_type, is_optional_row
from shared.text import clean_space


def rows_list(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    return [dict(row) for row in rows or [] if isinstance(row, Mapping)]


def row_text(row: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = str(row.get(key, "") or "").strip()
        if value: return value
    return ""


def row_day(row: Mapping[str, Any]) -> str: return row_text(row, "day", "day_label")
def row_city(row: Mapping[str, Any]) -> str: return row_text(row, "city", "destination", "location")
def is_main_row(row: Mapping[str, Any]) -> bool: return get_row_type(row) in CONTENT_TYPES and not is_optional_row(row)
def has_hotel_name(row: Mapping[str, Any]) -> bool: return bool(row_text(row, "hotel_name", "hotel", "accommodation", "title", "name"))


def normalise_fingerprint(value: str) -> str:
    text = clean_space(value).lower()
    return re.sub(r"[^a-z0-9à-ÿøåäö .'-]", "", text)[:160]


def row_fingerprint(row: Mapping[str, Any]) -> str:
    return "|".join((get_row_type(row), normalise_fingerprint(row_city(row)), normalise_fingerprint(row_text(row, "title", "original_title", "hotel_name", "name") or row_text(row, "details", "description"))))


def route_endpoint(row: Mapping[str, Any], *, destination: bool) -> str:
    keys = (("route_destination", "destination", "to", "to_city", "dropoff", "dropoff_place", "end_location") if destination else ("route_origin", "origin", "from", "from_city", "pickup", "pickup_place", "start_location"))
    value = row_text(row, *keys)
    if value: return value
    source = " - ".join(row_text(row, key) for key in ("title", "details", "description", "route", "original_title") if row_text(row, key))
    patterns = (
        r"\bfrom\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,45})\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,45})(?:\s+-\s+|\s+\||,|$)",
        r"\b(?:train|flight|coach|bus|ferry|cruise|transfer|private\s+transfer)\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,45})\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,45})(?:\s+-\s+|\s+\||,|$)",
        r"\b([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,45})\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,45})(?:\s+-\s+|\s+\||,|$)",
    )
    match = next((found for pattern in patterns if (found := re.search(pattern, source, flags=re.IGNORECASE))), None)
    if not match: return ""
    raw = re.sub(r"^(?:train|flight|coach|bus|ferry|cruise|transfer|private\s+transfer)\s+", "", match.group(2 if destination else 1), flags=re.IGNORECASE)
    return re.split(r"\b(?:hotel|station|airport|time|departure|arrival|onboard|included)\b", raw, maxsplit=1, flags=re.IGNORECASE)[0].strip(" -:|.,")


def day_text_weight(day_rows: Iterable[Mapping[str, Any]]) -> int:
    total = 0
    for row in day_rows:
        total += sum(len(str(row.get(key, "") or "")) for key in ("title", "details", "description", "client_description"))
        for key in ("includes", "notable_sights"):
            value = row.get(key)
            if isinstance(value, (list, tuple)): total += sum(len(str(item or "")) for item in value)
    return total


def primary_day_city(day_rows: Iterable[Mapping[str, Any]]) -> str:
    rows = list(day_rows)
    for row in rows:
        if get_row_type(row) == "Hotel" and row_city(row): return row_city(row)
    for row in rows:
        if get_row_type(row) in TRANSFER_TYPES and route_endpoint(row, destination=True): return route_endpoint(row, destination=True)
    return next((row_city(row) for row in rows if row_city(row)), "")

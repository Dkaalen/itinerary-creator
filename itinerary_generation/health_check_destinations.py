"""Destination-registry checks for itinerary rows."""

import re
from typing import Any, Mapping

from itinerary_generation.health_check_models import TRANSFER_TYPES
from itinerary_generation.health_check_rows import route_endpoint, row_city
from itinerary_generation.row_filters import get_row_type
from itinerary_generation.transport_safety import base_destination_from_terminal, normalize_transport_place

DESTINATION_FIELD_TYPES = {"Activity", "Cruise", "Ferry", "Flight", "Hotel", "Train", "Transfer", "Transport", "Self Drive", "Rental Car"}
DESTINATION_REVIEW_IGNORE = {"", "airport", "bus terminal", "cruise port", "hotel", "railway station", "station", "the accommodation", "your accommodation", "self transfer", "private transfer"}


def clean_destination_for_registry(value: object, *, strip_terminal: bool = True) -> str:
    text = normalize_transport_place(str(value or "").strip())
    text = re.sub(r"^(?:to|from|in|at)\s+", "", text, flags=re.IGNORECASE).strip(" -:|.,")
    text = re.sub(r"^(?:self|private)\s+transfer(?:\s+to)?\s*", "", text, flags=re.IGNORECASE).strip(" -:|.,")
    if strip_terminal:
        text = base_destination_from_terminal(text) or text
        text = re.sub(r"\b(?:train|rail|railway|bus|coach|cruise|ferry|airport)\s*$", "", text, flags=re.IGNORECASE).strip(" -:|.,")
    return re.sub(r"\b(?:your|the)\s+accommodation\b", "", text, flags=re.IGNORECASE).strip(" -:|.,")


def is_reviewable_destination(value: str) -> bool:
    text = str(value or "").strip()
    return bool(len(text) >= 3 and text.lower() not in DESTINATION_REVIEW_IGNORE and re.search(r"[A-Za-zÀ-ÿøØåÅäÄöÖðÐþÞ]", text) and not re.search(r"\b(?:self transfer|private transfer|meeting point|platform|tickets?|breakfast|standard room|double room|fjord lounge)\b", text, flags=re.IGNORECASE))


def destination_review_values(row: Mapping[str, Any]) -> list[tuple[str, str]]:
    row_type = get_row_type(row); values = []
    if row_type in DESTINATION_FIELD_TYPES and row_city(row): values.append(("city", row_city(row)))
    if row_type in TRANSFER_TYPES:
        for label, value in (("route origin", route_endpoint(row, destination=False)), ("route destination", route_endpoint(row, destination=True))):
            if value: values.append((label, value))
    clean, seen = [], set()
    for label, value in values:
        candidate = clean_destination_for_registry(value, strip_terminal=label != "city"); key = (label, candidate.lower())
        if candidate and key not in seen: seen.add(key); clean.append((label, candidate))
    return clean

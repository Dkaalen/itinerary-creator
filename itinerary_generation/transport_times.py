"""Shared transport schedule display helpers."""

from __future__ import annotations

import re

from shared.source_time_finders import find_clock_range
from shared.source_time_normalize import normalize_time_text
from itinerary_generation.transport_model import get_transport_source_text
from .inclusion_utils import clean
from shared.source_text_cleanup import clean_supplier_time


def get_overnight_train_schedule(row: dict) -> dict[str, str]:
    """Return departure/arrival details for sleeper-train rows when present."""

    source = clean(get_transport_source_text(row))
    if not source or not re.search(r"\b(?:santa\s+claus\s+express|overnight\s+train|night\s+train|sleeper)", source, flags=re.IGNORECASE):
        return {}

    # Common supplier style:
    # "... Santa Claus Express to Rovaniemi - 23:04 Helsinki - Arrival 10:58 Rovaniemi - cabin"
    match = re.search(
        r"(?:^|[-|])\s*(?P<dep>\d{1,2}:\d{2}\s*(?:am|pm)?)\s+(?P<origin>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)\s*[-|]\s*Arrival\s+(?P<arr>\d{1,2}:\d{2}\s*(?:am|pm)?)\s+(?P<destination>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)(?:\s*[-|]|$)",
        source,
        flags=re.IGNORECASE,
    )
    if match:
        return {
            "departure_time": normalize_time_text(match.group("dep")),
            "departure_place": clean(match.group("origin")).strip(" -:|.,"),
            "arrival_time": normalize_time_text(match.group("arr")),
            "arrival_place": clean(match.group("destination")).strip(" -:|.,"),
        }

    return {}


def get_transport_time_text(row: dict) -> str:
    """Return a client-facing time range for transport rows.

    Some supplier transport rows include schedule text only in the raw details.
    Keep one shared fallback so day pages and final inclusions do not drift.
    """

    time = clean_supplier_time(row.get("time", ""))
    if time:
        return time
    schedule = get_overnight_train_schedule(row)
    if schedule.get("departure_time") and schedule.get("arrival_time"):
        return f'{schedule["departure_time"]} - {schedule["arrival_time"]}'
    source = get_transport_source_text(row)
    labelled = re.search(
        r"\bdeparture\s*(?P<dep>\d{1,2}:\d{2}\s*(?:am|pm)?)\s*(?:[-–—,;|]\s*)?arrival\s*(?P<arr>\d{1,2}:\d{2}\s*(?:am|pm)?)",
        source,
        flags=re.IGNORECASE,
    )
    if labelled:
        return normalize_time_text(f"{labelled.group('dep')} - {labelled.group('arr')}")
    clock_range = find_clock_range(source)
    if clock_range:
        return normalize_time_text(clock_range)
    return ""

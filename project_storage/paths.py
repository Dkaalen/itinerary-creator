"""Deterministic storage paths for itinerary project files."""

from __future__ import annotations

import re
from datetime import datetime, timezone

_SAFE_SEGMENT_RE = re.compile(r"[^A-Za-z0-9._-]+")


def calculator_workbook_path(itinerary_id: str, filename: str) -> str:
    return f"itineraries/{safe_segment(itinerary_id)}/calculator/{timestamp()}-{safe_segment(filename)}"


def itinerary_snapshot_path(itinerary_id: str, itinerary_type: str, version_number: int) -> str:
    kind = safe_segment(itinerary_type or "agent")
    return f"itineraries/{safe_segment(itinerary_id)}/snapshots/{kind}-v{version_number:03d}.json"


def pdf_export_path(itinerary_id: str, itinerary_type: str, filename: str) -> str:
    kind = safe_segment(itinerary_type or "agent")
    return f"itineraries/{safe_segment(itinerary_id)}/exports/{kind}/{timestamp()}-{safe_segment(filename)}"


def safe_segment(value: str) -> str:
    cleaned = _SAFE_SEGMENT_RE.sub("-", str(value or "").strip()).strip("-._")
    return cleaned[:96] or "untitled"


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

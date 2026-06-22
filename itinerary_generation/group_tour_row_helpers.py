"""Source-row helpers for group-tour package detection and linking."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping

from itinerary_generation.group_tour_constants import _ITINERARY_DAY_RE, _PACKAGE_DAY_RE
from itinerary_generation.group_tour_text import _clean

def _row_type(row: Mapping[str, Any]) -> str:
    return _clean(row.get("effective_type") or row.get("type"))


def _row_text(row: Mapping[str, Any]) -> str:
    # Prefer the richest structured source.  Concatenating parser ``raw`` text
    # can reintroduce tabular prefixes and duplicate the same prose.
    for key in ("travel_element", "details", "description_raw", "description", "original_title", "title", "raw"):
        text = str(row.get(key) or "").strip()
        if text:
            return text
    return ""


def _group_tour_day_source(row: Mapping[str, Any]) -> str:
    """Return a package-day source beginning with its ``Day N`` label.

    Parsed text rows may keep an embedded city prefix (for example
    ``Reykjavík: Day 1: Golden Circle``), while workbook corpus rows begin
    directly with ``Day 1``.  The contract accepts both forms without
    scanning arbitrary later prose for a day marker.
    """

    for key in ("travel_element", "details", "original_title", "title", "description_raw", "description", "raw"):
        text = str(row.get(key) or "").strip().strip('"')
        if not text:
            continue
        direct = _PACKAGE_DAY_RE.match(text)
        if direct:
            return text
        prefixed = re.match(r"^\s*[^:\n]{1,80}:\s*(Day\s*\d+\s*(?::|\s*-\s*).*)$", text, re.I | re.S)
        if prefixed:
            return prefixed.group(1).strip()
    return _row_text(row)


def _source_row_id(row: Mapping[str, Any], source_name: str = "") -> str:
    row_id = _clean(row.get("row_id"))
    if row_id:
        return row_id
    excel_row = _clean(row.get("excel_row"))
    if excel_row:
        return f"{source_name or 'source'}:{excel_row}"
    digest = hashlib.sha256(_row_text(row).encode("utf-8")).hexdigest()[:12]
    return f"group-tour-{digest}"


def _itinerary_day_number(row: Mapping[str, Any]) -> int:
    match = _ITINERARY_DAY_RE.search(str(row.get("day") or ""))
    return int(match.group(1)) if match else 0

"""Contextual city fallback for sparse supplier rows.

Some calculator rows contain a valid day/type/date but only sparse text such as
``Departure`` or ``Private Airport to Hotel``.  The parser should use nearby real
city context for those rows instead of surfacing a client-facing blank city.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from place_aliases import canonicalize_place_name
from parser_modules.place_parsing import extract_route_points, is_valid_city_value
from parser_modules.row_quality import annotate_parser_quality
from parser_modules.text_cleanup import clean_space
from parser_modules.type_detection import normalize_type

_CONTEXTUAL_CITY_TYPES = {
    "Arrival",
    "Departure",
    "Hotel",
    "Activity",
    "Leisure",
    "Transfer",
    "Transport",
    "Train",
    "Flight",
    "Cruise",
    "Ferry",
}
_ROUTE_TYPES = {"Transfer", "Transport", "Train", "Flight", "Cruise", "Ferry"}
_LOCAL_SPARSE_TEXT_RE = re.compile(
    r"^(?:"
    r"arrival|departure|leisure\s+day|day\s+at\s+leisure|self\s+planned|group\s+tour|rental\s+car|"
    r"private\s+(?:airport\s+to\s+hotel|hotel\s+to\s+airport|transfer\s+to\s+(?:your\s+)?accommodation)|"
    r"private\s+transfer\s+from\s+(?:the\s+)?(?:airport|hotel)\s+to\s+(?:your\s+)?(?:accommodation|hotel|airport)|"
    r"self(?:[-\s]*arranged)?\s+transfer\s+(?:hotel\s+to\s+airport|airport\s+to\s+hotel|from\s+(?:the\s+)?(?:airport|hotel)\s+to\s+(?:your\s+)?(?:accommodation|hotel|airport))"
    r")$",
    flags=re.IGNORECASE,
)


def _row_type(row: Mapping[str, Any]) -> str:
    return normalize_type(str(row.get("effective_type") or row.get("type") or ""))


def _row_text(row: Mapping[str, Any]) -> str:
    return clean_space(" ".join(str(row.get(key, "") or "") for key in ("title", "details", "original_title")))


def _row_text_candidates(row: Mapping[str, Any]) -> tuple[str, ...]:
    candidates: list[str] = []
    seen: set[str] = set()
    for key in ("title", "details", "original_title"):
        value = clean_space(str(row.get(key, "") or ""))
        lowered = value.lower()
        if value and lowered not in seen:
            candidates.append(value)
            seen.add(lowered)
    return tuple(candidates)


def context_city_from_row(row: Mapping[str, Any]) -> str:
    """Return a row city that is safe to use as context for nearby rows."""

    city = canonicalize_place_name(clean_space(str(row.get("city", "") or "")))
    if city and is_valid_city_value(city):
        return city
    return ""


def _can_use_context_city(row: Mapping[str, Any]) -> bool:
    row_type = _row_type(row)
    if row_type not in _CONTEXTUAL_CITY_TYPES:
        return False

    text = _row_text(row)
    candidates = _row_text_candidates(row)
    if not text:
        return True

    if any(_LOCAL_SPARSE_TEXT_RE.match(candidate) for candidate in candidates):
        return True

    origin, destination = extract_route_points(text)
    if row_type in _ROUTE_TYPES and (origin or destination):
        return False

    if row_type in {"Arrival", "Departure", "Hotel", "Activity", "Leisure"}:
        return True

    return False


def apply_context_city(row: dict[str, Any], city: str) -> bool:
    """Fill a missing row city from nearby context when that is deterministic."""

    context_city = canonicalize_place_name(clean_space(city))
    if not context_city or row.get("city") or not _can_use_context_city(row):
        return False

    row["city"] = context_city
    annotate_parser_quality(row)
    return True

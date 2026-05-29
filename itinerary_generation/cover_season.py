"""Season detection helpers for itinerary covers."""

from __future__ import annotations

import re
from datetime import datetime

from itinerary_generation.cover_theme_constants import SEASON_ORDER


def normalize_cover_season(value: str) -> str:
    key = str(value or "").strip().lower()
    if key in SEASON_ORDER:
        return key
    return "automatic"


def _parse_month(value: str):
    text = str(value or "").strip()
    if not text:
        return None

    for fmt in ("%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).month
        except ValueError:
            pass

    match = re.search(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})\b", text)
    if match:
        month = int(match.group(2))
        if 1 <= month <= 12:
            return month
    return None


def _first_trip_month(parsed_rows) -> int | None:
    for row in parsed_rows or []:
        for key in ("start_date", "date", "end_date"):
            month = _parse_month(row.get(key, ""))
            if month:
                return month
    return None


def _details_text(parsed_rows) -> str:
    parts = []
    for row in parsed_rows or []:
        parts.extend([
            str(row.get("title", "")),
            str(row.get("original_title", "")),
            str(row.get("details", "")),
            str(row.get("city", "")),
        ])
        parts.extend(str(item) for item in row.get("includes", []) or [])
    return " ".join(parts).lower()


def has_winter_focus(parsed_rows) -> bool:
    text = _details_text(parsed_rows)
    winter_markers = [
        "winter", "snow", "lapland", "rovaniemi", "saariselkä", "saariselka",
        "northern light", "aurora", "reindeer", "husky", "santa", "arctic",
        "glass igloo", "kakslauttanen", "kakslauttenen", "ice floating", "snowmobile",
    ]
    return any(marker in text for marker in winter_markers)


def detect_cover_season(parsed_rows) -> str:
    """Infer a cover season from the itinerary date, with Nordic winter safeguards."""
    month = _first_trip_month(parsed_rows)
    winter_focus = has_winter_focus(parsed_rows)

    if month in {12, 1, 2, 3}:
        return "winter"
    if month in {4, 5}:
        return "spring"
    if month in {6, 7, 8}:
        return "summer"
    if month == 11 and winter_focus:
        return "winter"
    if month in {9, 10, 11}:
        return "autumn"
    if winter_focus:
        return "winter"
    return "summer"


def get_cover_season(parsed_rows, output_edits=None) -> str:
    selected = normalize_cover_season((output_edits or {}).get("cover_season", "automatic"))
    if selected != "automatic":
        return selected
    return detect_cover_season(parsed_rows)

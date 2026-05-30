"""Season detection helpers for itinerary covers."""

from __future__ import annotations

import re
from collections import Counter
from datetime import date, datetime, timedelta

from itinerary_generation.cover_theme_constants import SEASON_ORDER


def normalize_cover_season(value: str) -> str:
    key = str(value or "").strip().lower()
    if key in SEASON_ORDER:
        return key
    return "automatic"


def _parse_date(value: str) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None

    for fmt in ("%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass

    match = re.search(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})\b", text)
    if match:
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3))
        if year < 100:
            year += 2000
        try:
            return date(year, month, day)
        except ValueError:
            return None
    return None


def _parse_month(value: str):
    parsed = _parse_date(value)
    return parsed.month if parsed else None


def _row_date_range(row: dict) -> tuple[date, date] | None:
    starts = [_parse_date(row.get(key, "")) for key in ("start_date", "date")]
    ends = [_parse_date(row.get(key, "")) for key in ("end_date", "start_date", "date")]
    starts = [d for d in starts if d]
    ends = [d for d in ends if d]
    if not starts and not ends:
        return None
    start = min(starts or ends)
    end = max(ends or starts)
    if end < start:
        end = start
    return start, end


def _trip_date_range(parsed_rows) -> tuple[date, date] | None:
    ranges = [_row_date_range(row) for row in parsed_rows or []]
    ranges = [rng for rng in ranges if rng]
    if not ranges:
        return None
    return min(start for start, _ in ranges), max(end for _, end in ranges)


def _first_trip_month(parsed_rows) -> int | None:
    trip_range = _trip_date_range(parsed_rows)
    if trip_range:
        return trip_range[0].month
    for row in parsed_rows or []:
        for key in ("start_date", "date", "end_date"):
            month = _parse_month(row.get(key, ""))
            if month:
                return month
    return None


def _season_for_date(day: date) -> str:
    if day.month in {12, 1, 2, 3}:
        return "winter"
    if day.month in {4, 5}:
        return "spring"
    if day.month in {6, 7, 8}:
        return "summer"
    return "autumn"


def _dominant_trip_season(parsed_rows) -> str | None:
    trip_range = _trip_date_range(parsed_rows)
    if not trip_range:
        return None
    start, end = trip_range
    counts: Counter[str] = Counter()
    current = start
    while current <= end:
        counts[_season_for_date(current)] += 1
        current += timedelta(days=1)

    if not counts:
        return None

    max_days = max(counts.values())
    winners = {season for season, days in counts.items() if days == max_days}
    if "winter" in winners:
        return "winter"
    start_season = _season_for_date(start)
    if start_season in winners:
        return start_season
    for season in ["summer", "autumn", "spring"]:
        if season in winners:
            return season
    return counts.most_common(1)[0][0]


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
    """Infer the dominant Nordic travel season for the itinerary cover."""

    dominant = _dominant_trip_season(parsed_rows)
    if dominant:
        return dominant

    month = _first_trip_month(parsed_rows)
    winter_focus = has_winter_focus(parsed_rows)

    if month in {12, 1, 2, 3}:
        return "winter"
    if month in {4, 5}:
        return "spring"
    if month in {6, 7, 8}:
        return "summer"
    if month in {9, 10, 11}:
        return "winter" if month == 11 and winter_focus else "autumn"
    if winter_focus:
        return "winter"
    return "summer"


def get_cover_season(parsed_rows, output_edits=None) -> str:
    selected = normalize_cover_season((output_edits or {}).get("cover_season", "automatic"))
    if selected != "automatic":
        return selected
    return detect_cover_season(parsed_rows)

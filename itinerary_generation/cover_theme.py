"""Seasonal cover helpers for itinerary preview and PDF export.

The cover system uses curated static background artwork from
``assets/cover_backgrounds`` and renders all text in the app. This keeps cover
copy editable while giving the first page a stable, premium visual style.
"""

from __future__ import annotations

import base64
import mimetypes
import re
from datetime import datetime
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
COVER_BACKGROUND_DIR = APP_ROOT / "assets" / "cover_backgrounds"

SEASON_LABELS = {
    "winter": "Winter",
    "spring": "Spring",
    "summer": "Summer",
    "autumn": "Autumn",
}

SEASON_ORDER = ["automatic", "winter", "spring", "summer", "autumn"]

SEASON_SUBTITLES = {
    "winter": "A premium Nordic winter journey with scenic travel and Arctic experiences",
    "spring": "A premium spring journey with scenic travel and curated experiences",
    "summer": "A premium summer journey with scenic travel and curated experiences",
    "autumn": "A premium autumn journey with scenic travel and curated experiences",
}

SEASON_TITLES = {
    "winter": "Nordic Winter Journey",
    "spring": "Nordic Spring Journey",
    "summer": "Nordic Summer Journey",
    "autumn": "Nordic Autumn Journey",
}

SEASON_TEXT_COLORS = {
    "winter": {"ink": "#1f3446", "muted": "#7b746c", "accent": "#b89555"},
    "spring": {"ink": "#2e563f", "muted": "#7b7a66", "accent": "#b99a58"},
    "summer": {"ink": "#2c5a42", "muted": "#747865", "accent": "#b99a58"},
    "autumn": {"ink": "#35513f", "muted": "#7e6f5b", "accent": "#bb8b45"},
}


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


def get_cover_background_path(season: str) -> Path | None:
    key = normalize_cover_season(season)
    if key == "automatic":
        key = "summer"
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        candidate = COVER_BACKGROUND_DIR / f"{key}{ext}"
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def image_to_data_uri(path: Path | None) -> str:
    if not path:
        return ""
    try:
        path = Path(path)
        if not path.exists() or not path.is_file():
            return ""
        mime = mimetypes.guess_type(str(path))[0] or "image/png"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"
    except Exception:
        return ""


def get_cover_theme(parsed_rows, output_edits=None) -> dict:
    season = get_cover_season(parsed_rows, output_edits)
    path = get_cover_background_path(season)
    colors = SEASON_TEXT_COLORS.get(season, SEASON_TEXT_COLORS["summer"])
    return {
        "season": season,
        "season_label": SEASON_LABELS.get(season, "Summer"),
        "title": SEASON_TITLES.get(season, SEASON_TITLES["summer"]),
        "subtitle": SEASON_SUBTITLES.get(season, SEASON_SUBTITLES["summer"]),
        "background_path": str(path) if path else "",
        "background_data_uri": image_to_data_uri(path),
        "ink": colors["ink"],
        "muted": colors["muted"],
        "accent": colors["accent"],
    }

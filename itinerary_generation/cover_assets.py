"""Cover background asset helpers."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from itinerary_generation.cover_season import get_cover_season, normalize_cover_season
from itinerary_generation.cover_theme_constants import (
    COVER_BACKGROUND_DIR,
    SEASON_LABELS,
    SEASON_SUBTITLES,
    SEASON_TEXT_COLORS,
    SEASON_TITLES,
)


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

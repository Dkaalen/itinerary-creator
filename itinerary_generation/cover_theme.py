"""Compatibility facade for seasonal cover helpers."""

from __future__ import annotations

from itinerary_generation.cover_assets import get_cover_background_path, get_cover_theme, image_to_data_uri
from itinerary_generation.cover_season import (
    _details_text,
    _first_trip_month,
    _parse_month,
    detect_cover_season,
    get_cover_season,
    has_winter_focus,
    normalize_cover_season,
)
from itinerary_generation.cover_theme_constants import (
    APP_ROOT,
    COVER_BACKGROUND_DIR,
    SEASON_LABELS,
    SEASON_ORDER,
    SEASON_SUBTITLES,
    SEASON_TEXT_COLORS,
    SEASON_TITLES,
)

__all__ = [
    "APP_ROOT",
    "COVER_BACKGROUND_DIR",
    "SEASON_LABELS",
    "SEASON_ORDER",
    "SEASON_SUBTITLES",
    "SEASON_TEXT_COLORS",
    "SEASON_TITLES",
    "_details_text",
    "_first_trip_month",
    "_parse_month",
    "detect_cover_season",
    "get_cover_background_path",
    "get_cover_season",
    "get_cover_theme",
    "has_winter_focus",
    "image_to_data_uri",
    "normalize_cover_season",
]

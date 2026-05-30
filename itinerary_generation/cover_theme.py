"""Compatibility facade for seasonal cover helpers."""

from __future__ import annotations

from itinerary_generation.cover_assets import get_cover_background_path, get_cover_theme, image_to_data_uri
from itinerary_generation.cover_background_selector import (
    count_rail_travel_rows,
    has_northern_lights_activity,
    select_cover_background_key,
)
from itinerary_generation.cover_season import (
    _details_text,
    _first_trip_month,
    _dominant_trip_season,
    _parse_date,
    _parse_month,
    _season_for_date,
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
    "_dominant_trip_season",
    "_parse_date",
    "_parse_month",
    "_season_for_date",
    "count_rail_travel_rows",
    "detect_cover_season",
    "get_cover_background_path",
    "get_cover_season",
    "get_cover_theme",
    "has_northern_lights_activity",
    "has_winter_focus",
    "image_to_data_uri",
    "normalize_cover_season",
    "select_cover_background_key",
]

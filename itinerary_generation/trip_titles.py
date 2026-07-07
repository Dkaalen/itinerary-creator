from __future__ import annotations

import re

from itinerary_generation.cover_route import create_cover_route_line
from itinerary_generation.common import (
    get_day_count,
    get_destination_countries,
    get_row_type,
    get_unique_cities,
    has_self_drive_markers,
    main_rows_only,
)
from itinerary_generation.cover_theme import (
    SEASON_LABELS,
    SEASON_SUBTITLES,
    SEASON_TITLES,
    detect_cover_season,
    has_winter_focus,
)
from itinerary_generation.group_tour_rendering import group_tour_package_from_rows
from itinerary_generation.trip_brain import create_trip_subtitle_from_brain, create_trip_title_from_brain

def create_trip_title(parsed_rows, grouped_days):
    return create_trip_title_from_brain(parsed_rows, grouped_days)


def _join_destinations_naturally(cities):
    clean_cities = [str(city or "").strip() for city in cities if str(city or "").strip()]
    if not clean_cities:
        return "the Nordics"
    if len(clean_cities) == 1:
        return clean_cities[0]
    if len(clean_cities) == 2:
        return f"{clean_cities[0]} and {clean_cities[1]}"
    return ", ".join(clean_cities[:-1]) + f" and {clean_cities[-1]}"


def _indefinite_article(scope: str) -> str:
    return "An" if str(scope or "").strip().lower()[:1] in {"a", "e", "i", "o", "u"} else "A"


def create_trip_subtitle(parsed_rows, grouped_days):
    return create_trip_subtitle_from_brain(parsed_rows, grouped_days)


def create_destinations_line(parsed_rows):
    return create_cover_route_line(parsed_rows)


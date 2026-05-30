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

def create_trip_title(parsed_rows, grouped_days):
    parsed_rows = main_rows_only(parsed_rows)
    cities = get_unique_cities(parsed_rows)
    day_count = get_day_count(grouped_days)
    season = detect_cover_season(parsed_rows)
    season_label = SEASON_LABELS.get(season, "Summer")
    countries = get_destination_countries(parsed_rows)
    text = " ".join(f'{row.get("title", "")} {row.get("original_title", "")} {row.get("details", "")}' for row in parsed_rows).lower()

    is_group_tour = any(marker in text for marker in ["group tour", "holiday package", "sharing room basis"])
    has_cruise_heavy = sum(1 for row in parsed_rows if get_row_type(row) == "Cruise") >= 3
    has_nutshell = "norway in a nutshell" in text or ("flåm" in text or "flam" in text) and ("nærøyfjord" in text or "naeroyfjord" in text)
    has_aurora = any(marker in text for marker in ["northern light", "aurora", "icehotel", "kiruna", "svalbard", "lapland"])
    has_western_norway = set(cities).intersection({"Bergen", "Ålesund", "Geiranger", "Solvorn", "Flåm", "Myrdal"}) and len(set(cities)) >= 3 and countries == ["Norway"]

    if is_group_tour and countries == ["Iceland"]:
        if "snæfellsnes" in text or "snaefellsnes" in text:
            return "Snæfellsnes & South Coast Adventure"
        return "Iceland Guided Discovery"

    if has_western_norway:
        return "Western Norway Scenic Escape"
    if has_cruise_heavy and len(countries) >= 2:
        return "Scandinavian Coastal Voyage" if set(countries).issubset({"Norway", "Sweden", "Denmark"}) else "Nordic Coastal Voyage"
    if has_aurora and countries == ["Sweden"]:
        return "Swedish Lapland Aurora Break"
    if has_aurora and countries == ["Norway"] and any(city in cities for city in ["Tromsø", "Svalbard", "Kiruna"]):
        return "Arctic Norway Adventure"
    if has_nutshell and countries == ["Norway"]:
        return "Norway Fjord & Rail Journey"

    if len(countries) == 1:
        country = countries[0]
        if season in {"spring", "summer", "autumn"}:
            return f"{country} {season_label} Escape"
        return f"{country} {season_label} Journey"

    scandinavian = {"Norway", "Sweden", "Denmark"}
    nordic = scandinavian | {"Finland", "Iceland", "Estonia"}
    country_set = set(countries)
    if len(country_set) >= 2 and country_set.issubset(scandinavian):
        return f"Scandinavian {season_label} Discovery"
    if len(country_set) >= 2 and country_set.issubset(nordic):
        if has_aurora:
            return "Lapland & Norway Northern Lights Escape"
        return f"Nordic {season_label} Highlights"

    if len(cities) == 1:
        city = cities[0]
        if has_aurora:
            return f"{city} Northern Lights Journey"
        return f"{city} {season_label} Journey"

    if len(cities) >= 2:
        return SEASON_TITLES.get(season, f"{season_label} Journey")

    if day_count >= 10:
        return "Grand Nordic Journey"

    return "Nordic Discovery Journey"


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
    parsed_rows = main_rows_only(parsed_rows)
    season = detect_cover_season(parsed_rows)
    season_label = SEASON_LABELS.get(season, "summer").lower()
    countries = get_destination_countries(parsed_rows)
    scope = countries[0] if len(countries) == 1 else "Nordic"
    article = _indefinite_article(scope)
    if has_self_drive_markers(parsed_rows):
        return f"{article} {scope} {season_label} self-drive journey with scenic routes and planned experiences"
    if season in SEASON_SUBTITLES:
        if len(countries) == 1:
            return f"{article} {scope} {season_label} journey with scenic travel and planned experiences"
        return SEASON_SUBTITLES[season]
    if has_winter_focus(parsed_rows):
        return SEASON_SUBTITLES["winter"]
    return "A carefully planned Nordic journey with smooth travel and included experiences"


def create_destinations_line(parsed_rows):
    return create_cover_route_line(parsed_rows)


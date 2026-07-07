"""Trip Brain.

Owns trip-level wording: title, subtitle and geography sanity. It keeps cover
copy aligned with the whole route rather than a single destination cluster.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Sequence

from itinerary_generation.common import get_day_count, get_destination_countries, get_row_type, get_unique_cities, has_self_drive_markers, main_rows_only
from itinerary_generation.cover_theme import SEASON_LABELS, SEASON_SUBTITLES, SEASON_TITLES, detect_cover_season, has_winter_focus
from itinerary_generation.group_tour_rendering import group_tour_package_from_rows

_ARCTIC_NORWAY = {"Tromsø", "Tromso", "Alta", "Kirkenes", "Svalbard", "Longyearbyen", "Narvik"}
_WESTERN_NORWAY = {"Bergen", "Ålesund", "Alesund", "Geiranger", "Solvorn", "Flåm", "Flam", "Myrdal", "Voss", "Stavanger"}
_CAPITAL_GATEWAYS = {"Oslo"}


@dataclass(frozen=True)
class TripBrainProfile:
    cities: tuple[str, ...]
    countries: tuple[str, ...]
    season: str
    day_count: int
    has_aurora: bool = False
    has_cruise_heavy: bool = False
    has_nutshell: bool = False
    has_western_norway: bool = False
    has_arctic_norway: bool = False
    is_group_tour: bool = False
    is_self_drive: bool = False


def build_trip_brain_profile(parsed_rows: Sequence[Mapping[str, object]] | None, grouped_days: Mapping[str, Sequence[Mapping[str, object]]] | None) -> TripBrainProfile:
    rows = main_rows_only([dict(row) for row in (parsed_rows or []) if isinstance(row, Mapping)])
    cities = tuple(get_unique_cities(rows))
    countries = tuple(get_destination_countries(rows))
    season = detect_cover_season(rows)
    text = " ".join(str(row.get(key, "")) for row in rows for key in ("title", "original_title", "details")).lower()
    group_tour_package = group_tour_package_from_rows(rows)
    city_set = set(cities)
    return TripBrainProfile(
        cities=cities,
        countries=countries,
        season=season,
        day_count=get_day_count(grouped_days or {}),
        has_aurora=any(marker in text for marker in ["northern light", "aurora", "icehotel", "kiruna", "svalbard", "lapland", "tromsø", "tromso"]),
        has_cruise_heavy=sum(1 for row in rows if get_row_type(row) == "Cruise") >= 3,
        has_nutshell="norway in a nutshell" in text or (("flåm" in text or "flam" in text) and ("nærøyfjord" in text or "naeroyfjord" in text)),
        has_western_norway=bool(city_set & _WESTERN_NORWAY),
        has_arctic_norway=bool(city_set & _ARCTIC_NORWAY),
        is_group_tour=group_tour_package is not None or any(marker in text for marker in ["group tour", "holiday package", "sharing room basis"]),
        is_self_drive=has_self_drive_markers(rows),
    )


def create_trip_title_from_brain(parsed_rows: Sequence[Mapping[str, object]] | None, grouped_days: Mapping[str, Sequence[Mapping[str, object]]] | None) -> str:
    profile = build_trip_brain_profile(parsed_rows, grouped_days)
    countries = list(profile.countries)
    cities = list(profile.cities)
    season_label = SEASON_LABELS.get(profile.season, "Summer")

    if profile.is_group_tour and countries == ["Iceland"]:
        text = " ".join(str(row.get(key, "")) for row in main_rows_only(list(parsed_rows or [])) for key in ("title", "details", "original_title")).lower()
        if "snæfellsnes" in text or "snaefellsnes" in text:
            return "Snæfellsnes & South Coast Adventure"
        return "Iceland Guided Discovery"

    if countries == ["Norway"] and profile.has_arctic_norway and profile.has_western_norway:
        return "Norway Winter Highlights" if profile.season == "winter" else "Norway Scenic Highlights"
    if countries == ["Norway"] and profile.has_arctic_norway and len(cities) >= 2:
        return "Norway Arctic Winter Journey" if profile.season == "winter" else "Arctic Norway Adventure"
    if countries == ["Norway"] and profile.has_western_norway and len(set(cities) - _CAPITAL_GATEWAYS) >= 2:
        return "Western Norway Scenic Escape"
    if profile.has_cruise_heavy and len(countries) >= 2:
        return "Scandinavian Coastal Voyage" if set(countries).issubset({"Norway", "Sweden", "Denmark"}) else "Nordic Coastal Voyage"
    if profile.has_nutshell and countries == ["Norway"]:
        return "Norway Fjord & Rail Journey"
    if profile.has_aurora and countries == ["Sweden"]:
        return "Swedish Lapland Northern Lights Break"

    if len(countries) == 1:
        country = countries[0]
        if profile.season in {"spring", "summer", "autumn"}:
            return f"{country} {season_label} Escape"
        return f"{country} {season_label} Journey"

    scandinavian = {"Norway", "Sweden", "Denmark"}
    nordic = scandinavian | {"Finland", "Iceland", "Estonia"}
    country_set = set(countries)
    if len(country_set) >= 2 and country_set.issubset(scandinavian):
        return f"Scandinavian {season_label} Discovery"
    if len(country_set) >= 2 and country_set.issubset(nordic):
        if profile.has_aurora:
            return "Lapland & Norway Northern Lights Escape"
        return f"Nordic {season_label} Highlights"

    if len(cities) == 1:
        city = cities[0]
        if profile.has_aurora:
            return f"{city} Northern Lights Journey"
        return f"{city} {season_label} Journey"
    if len(cities) >= 2:
        return SEASON_TITLES.get(profile.season, f"{season_label} Journey")
    if profile.day_count >= 10:
        return "Grand Nordic Journey"
    return "Nordic Discovery Journey"


def create_trip_subtitle_from_brain(parsed_rows: Sequence[Mapping[str, object]] | None, grouped_days: Mapping[str, Sequence[Mapping[str, object]]] | None) -> str:
    rows = main_rows_only([dict(row) for row in (parsed_rows or []) if isinstance(row, Mapping)])
    profile = build_trip_brain_profile(rows, grouped_days)
    group_tour_package = group_tour_package_from_rows(rows)
    countries = list(profile.countries)
    season_label = SEASON_LABELS.get(profile.season, "summer").lower()
    scope = countries[0] if len(countries) == 1 else "Nordic"
    article = "An" if str(scope).lower()[:1] in {"a", "e", "i", "o", "u"} else "A"
    if group_tour_package is not None:
        season_text = f" {group_tour_package.season}" if group_tour_package.season in {"summer", "winter"} else ""
        return f"A guided{season_text} Iceland group tour with arranged transport, daily experiences and included accommodation"
    if profile.is_self_drive:
        return f"{article} {scope} {season_label} self-drive journey with scenic routes and planned experiences"
    if profile.has_arctic_norway and profile.has_western_norway and countries == ["Norway"]:
        return "A Norway winter journey combining scenic rail travel, Arctic experiences and northern lights activities"
    if profile.season in SEASON_SUBTITLES:
        if len(countries) == 1:
            return f"{article} {scope} {season_label} journey with scenic travel and planned experiences"
        return SEASON_SUBTITLES[profile.season]
    if has_winter_focus(rows):
        return SEASON_SUBTITLES["winter"]
    return "A carefully planned Nordic journey with smooth travel and included experiences"


__all__ = ["TripBrainProfile", "build_trip_brain_profile", "create_trip_subtitle_from_brain", "create_trip_title_from_brain"]

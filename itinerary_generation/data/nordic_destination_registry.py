"""Structured Nordic destination registry built from the legacy place list.

The parser still depends on ``place_alias_data.PLACES``.  This module adds a
richer read model on top of that source so copy, image and route systems can
scale to hundreds of useful Nordic itinerary destinations without each feature
maintaining its own hardcoded city list.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

from place_alias_data import PLACES
from place_alias_text import normalize_place_key

from itinerary_generation.data.nordic_destination_registry_data import (
    AIR_HUB_NAMES,
    ARCTIC_FINLAND,
    ARCTIC_NORWAY,
    ARCTIC_SWEDEN,
    CRUISE_PORTS,
    DENMARK_REGION_OVERRIDES,
    FINLAND_REGION_OVERRIDES,
    ICELAND_REGION_OVERRIDES,
    NORWAY_REGION_OVERRIDES,
    RAIL_HUBS,
    REGION_FALLBACKS,
    SOUTHERN_COASTAL_DENMARK,
    SOUTHERN_COASTAL_FINLAND,
    SOUTHERN_COASTAL_NORWAY,
    SOUTHERN_COASTAL_SWEDEN,
    SWEDEN_REGION_OVERRIDES,
    TRAVEL_DESTINATION_KINDS,
)


@dataclass(frozen=True)
class NordicDestination:
    name: str
    country: str
    region: str
    destination_type: str
    aliases: tuple[str, ...]
    nearby_hubs: tuple[str, ...]
    season_profile: str
    image_profile: str
    copy_profile: str
    transport_role: tuple[str, ...]
    priority: int



















def _aliases(place: dict) -> tuple[str, ...]:
    return tuple(str(alias).strip() for alias in place.get("aliases", ()) if str(alias).strip())


def _region(place: dict) -> str:
    name = str(place.get("canonical", ""))
    country = str(place.get("country", ""))
    if country == "Norway":
        return NORWAY_REGION_OVERRIDES.get(name, REGION_FALLBACKS.get(country, country))
    if country == "Sweden":
        return SWEDEN_REGION_OVERRIDES.get(name, REGION_FALLBACKS.get(country, country))
    if country == "Finland":
        return FINLAND_REGION_OVERRIDES.get(name, REGION_FALLBACKS.get(country, country))
    if country == "Denmark":
        return DENMARK_REGION_OVERRIDES.get(name, REGION_FALLBACKS.get(country, country))
    if country == "Iceland":
        return ICELAND_REGION_OVERRIDES.get(name, REGION_FALLBACKS.get(country, country))
    return REGION_FALLBACKS.get(country, country)


def _season_profile(place: dict) -> str:
    name = str(place.get("canonical", ""))
    country = str(place.get("country", ""))
    kind = str(place.get("kind", ""))
    if country == "Norway" and name in ARCTIC_NORWAY:
        return "arctic"
    if country == "Sweden" and name in ARCTIC_SWEDEN:
        return "arctic"
    if country == "Finland" and name in ARCTIC_FINLAND:
        return "arctic"
    if country == "Norway" and name in SOUTHERN_COASTAL_NORWAY:
        return "southern_coastal"
    if country == "Sweden" and name in SOUTHERN_COASTAL_SWEDEN:
        return "southern_coastal"
    if country == "Finland" and name in SOUTHERN_COASTAL_FINLAND:
        return "southern_coastal"
    if country == "Denmark" and name in SOUTHERN_COASTAL_DENMARK:
        return "southern_coastal"
    if country == "Iceland":
        region = ICELAND_REGION_OVERRIDES.get(name, "Iceland")
        if region == "Icelandic Highlands":
            return "iceland_highland"
        if region in {"North Iceland", "Westfjords", "East Iceland", "Southeast Iceland", "Vatnajökull Region"}:
            return "iceland_scenic"
        return "iceland_all_season"
    if kind in {"resort", "national_park"}:
        return "mountain"
    if kind in {"fjord", "island"}:
        return "coastal_nature"
    return "standard_nordic"


def _image_profile(place: dict) -> str:
    name = str(place.get("canonical", ""))
    country = str(place.get("country", ""))
    kind = str(place.get("kind", ""))
    if country == "Iceland":
        region = ICELAND_REGION_OVERRIDES.get(name, "Iceland")
        if kind == "route":
            return "iceland_route"
        if name in {"Blue Lagoon", "Sky Lagoon"}:
            return "thermal_lagoon"
        if region == "Icelandic Highlands":
            return "iceland_highland"
        if kind == "national_park":
            return "iceland_national_park"
        if kind in {"waterfall", "beach", "lagoon", "lake", "attraction"}:
            return "iceland_landmark"
        if name in CRUISE_PORTS:
            return "cruise_port"
        return "iceland_destination"
    if name in SOUTHERN_COASTAL_NORWAY or name in SOUTHERN_COASTAL_SWEDEN or name in SOUTHERN_COASTAL_FINLAND or name in SOUTHERN_COASTAL_DENMARK:
        return "southern_coastal"
    if name in ARCTIC_NORWAY or name in ARCTIC_SWEDEN or name in ARCTIC_FINLAND:
        return "arctic"
    if kind == "fjord":
        return "fjord"
    if kind == "island":
        return "island_coastal"
    if kind == "national_park":
        return "national_park"
    if kind == "resort":
        return "mountain_resort"
    if name in CRUISE_PORTS:
        return "cruise_port"
    if name in RAIL_HUBS:
        return "rail_hub"
    return kind or "destination"


def _copy_profile(place: dict) -> str:
    kind = str(place.get("kind", ""))
    country = str(place.get("country", ""))
    image_profile = _image_profile(place)
    if country == "Iceland":
        if image_profile in {"thermal_lagoon"}:
            return "thermal_lagoon"
        if kind == "route":
            return "scenic_route"
        if kind in {"national_park", "region", "fjord", "island"}:
            return "icelandic_nature"
        if kind in {"city", "town", "village"}:
            return "icelandic_town"
        return "icelandic_landmark"
    if image_profile in {"southern_coastal", "cruise_port"}:
        return "coastal_city"
    if image_profile == "arctic":
        return "arctic"
    if kind in {"fjord", "village"}:
        return "scenic_nature"
    if kind == "resort":
        return "mountain_resort"
    if kind == "national_park":
        return "national_park"
    if kind == "route":
        return "scenic_route"
    return "urban_culture" if kind in {"city", "town"} else "destination"


def _transport_role(place: dict) -> tuple[str, ...]:
    name = str(place.get("canonical", ""))
    roles: list[str] = []
    if name in AIR_HUB_NAMES or place.get("kind") == "airport":
        roles.append("air_hub")
    if name in RAIL_HUBS:
        roles.append("rail_hub")
    if name in CRUISE_PORTS:
        roles.append("cruise_port")
    if place.get("kind") in {"fjord", "route"}:
        roles.append("scenic_route")
    if place.get("kind") == "national_park":
        roles.append("nature_gateway")
    return tuple(roles or ("destination",))


def _priority(place: dict) -> int:
    name = str(place.get("canonical", ""))
    kind = str(place.get("kind", ""))
    if name in {"Oslo", "Bergen", "Stavanger", "Kristiansand", "Tromsø", "Trondheim", "Ålesund", "Flåm", "Geiranger", "Stockholm", "Gothenburg", "Malmö", "Kiruna", "Abisko", "Åre", "Visby", "Helsinki", "Rovaniemi", "Turku", "Tampere", "Levi", "Saariselkä", "Porvoo", "Åland", "Copenhagen", "Aarhus", "Odense", "Aalborg", "Billund", "Roskilde", "Helsingør", "Skagen", "Bornholm", "Reykjavík", "Keflavík", "Blue Lagoon", "Golden Circle", "South Coast", "Vík", "Jökulsárlón", "Skaftafell", "Vatnajökull", "Akureyri", "Mývatn", "Húsavík", "Snæfellsnes", "Ísafjörður", "Westfjords", "Landmannalaugar", "Ring Road"}:
        return 100
    if name in CRUISE_PORTS or name in RAIL_HUBS:
        return 85
    if kind in {"city", "town"}:
        return 70
    if kind in {"village", "resort", "fjord", "national_park", "island"}:
        return 60
    return 40


def _nearby_hubs(place: dict) -> tuple[str, ...]:
    country = str(place.get("country", ""))
    region = _region(place)
    if country == "Iceland":
        if region in {"Capital Region", "Reykjanes", "Golden Circle", "West Iceland"}:
            return ("Reykjavík", "Keflavík")
        if region in {"South Iceland", "South Coast and Islands", "Vatnajökull Region", "Southeast Iceland"}:
            return ("Reykjavík", "Vík", "Höfn")
        if region in {"Snæfellsnes", "Westfjords"}:
            return ("Reykjavík", "Ísafjörður", "Stykkishólmur")
        if region == "North Iceland":
            return ("Akureyri", "Húsavík")
        if region == "East Iceland":
            return ("Egilsstaðir", "Seyðisfjörður")
        if region == "Icelandic Highlands":
            return ("Reykjavík", "Akureyri")
        if region == "Iceland Ring Road":
            return ("Reykjavík", "Akureyri", "Höfn")
    if region in {"Sognefjord", "Hardanger", "Western Norway", "Nordfjord", "Sunnfjord"}:
        return ("Bergen",)
    if region in {"Southern Norway", "Rogaland"}:
        return ("Kristiansand", "Stavanger")
    if region in {"Lofoten", "Northern Norway"}:
        return ("Bodø", "Tromsø")
    if region == "Trøndelag":
        return ("Trondheim",)
    if region in {"Eastern Norway", "Oslofjord", "Vestfold and Telemark"}:
        return ("Oslo",)
    if region in {"Stockholm and Central Sweden", "Stockholm Archipelago", "Central Sweden", "Östergötland"}:
        return ("Stockholm",)
    if region in {"West Sweden", "Värmland"}:
        return ("Gothenburg",)
    if region == "Skåne":
        return ("Malmö", "Copenhagen")
    if region in {"Småland and Islands", "Gotland and Öland"}:
        return ("Stockholm", "Malmö")
    if region in {"Dalarna", "Gävleborg"}:
        return ("Stockholm",)
    if region in {"High Coast", "Jämtland Härjedalen"}:
        return ("Sundsvall", "Östersund")
    if region == "Swedish Lapland":
        return ("Luleå", "Kiruna")
    if region in {"Capital Region", "Southern Coast", "Southern Finland"}:
        return ("Helsinki",)
    if region in {"Southwest Finland", "Åland and Archipelago"}:
        return ("Turku", "Helsinki")
    if region in {"West Coast", "Ostrobothnia"}:
        return ("Vaasa", "Turku")
    if region in {"Finnish Lakeland", "North Karelia"}:
        return ("Tampere", "Kuopio")
    if region in {"Northern Ostrobothnia", "Kainuu"}:
        return ("Oulu", "Kajaani")
    if region == "Finnish Lapland":
        return ("Rovaniemi", "Kittilä", "Ivalo")
    if region in {"Greater Copenhagen", "North Zealand", "Zealand", "South Zealand and Islands"}:
        return ("Copenhagen", "Roskilde")
    if region == "Bornholm":
        return ("Copenhagen", "Rønne")
    if region in {"Funen and Islands", "Danish Islands"}:
        return ("Odense", "Copenhagen")
    if region in {"East Jutland", "South Jutland"}:
        return ("Aarhus", "Billund", "Copenhagen")
    if region == "West Jutland":
        return ("Billund", "Esbjerg")
    if region == "North Jutland":
        return ("Aalborg", "Aarhus")
    return ()


def destination_from_place(place: dict) -> NordicDestination:
    return NordicDestination(
        name=str(place.get("canonical", "")).strip(),
        country=str(place.get("country", "")).strip(),
        region=_region(place),
        destination_type=str(place.get("kind", "")).strip() or "destination",
        aliases=_aliases(place),
        nearby_hubs=_nearby_hubs(place),
        season_profile=_season_profile(place),
        image_profile=_image_profile(place),
        copy_profile=_copy_profile(place),
        transport_role=_transport_role(place),
        priority=_priority(place),
    )


@lru_cache(maxsize=1)
def registry_records() -> tuple[NordicDestination, ...]:
    return tuple(destination_from_place(place) for place in PLACES)


def travel_destination_records(records: Iterable[NordicDestination] | None = None) -> tuple[NordicDestination, ...]:
    source = tuple(records) if records is not None else registry_records()
    return tuple(record for record in source if record.destination_type in TRAVEL_DESTINATION_KINDS)


def _normalise(value: object) -> str:
    """Compatibility wrapper around the canonical Nordic place-key owner."""

    return normalize_place_key(value)


@lru_cache(maxsize=1)
def alias_index() -> dict[str, NordicDestination]:
    index: dict[str, NordicDestination] = {}
    for record in registry_records():
        values = (record.name, *record.aliases)
        for value in values:
            key = _normalise(value)
            if key and key not in index:
                index[key] = record
    return index


def destination_for_alias(value: object) -> NordicDestination | None:
    return alias_index().get(_normalise(value))


def destination_country_for_alias(value: object) -> str:
    record = destination_for_alias(value)
    return record.country.lower() if record else ""


def registry_city_aliases() -> dict[str, set[str]]:
    aliases: dict[str, set[str]] = {}
    for record in registry_records():
        if record.destination_type not in TRAVEL_DESTINATION_KINDS:
            continue
        key = _normalise(record.name)
        if not key:
            continue
        aliases.setdefault(key, set()).add(record.name)
        aliases[key].update(record.aliases)
    return aliases


def is_southern_coastal_destination(value: object) -> bool:
    record = destination_for_alias(value)
    return bool(record and record.season_profile == "southern_coastal")

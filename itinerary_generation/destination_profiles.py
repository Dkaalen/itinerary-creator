"""Deterministic destination copy profiles for Nordic itinerary text.

The registry already knows which places the product can recognise. This module
turns every registered travel destination into reusable copy ingredients so day
intros and free-time text can stay destination-aware without adding one-off
logic for a single itinerary.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import re
from typing import Iterable, Mapping, Sequence

from itinerary_generation.destination_registry import (
    NordicDestination,
    destination_for_alias,
    travel_destination_records,
)
from text_polish import polish_title


@dataclass(frozen=True)
class DestinationProfile:
    name: str
    country: str
    region: str
    destination_type: str
    copy_profile: str
    aliases: tuple[str, ...]
    identity: str
    arrival_identity: str
    leisure_identity: str
    atmosphere: tuple[str, ...]
    hooks: tuple[str, ...]
    arrival_templates: tuple[str, ...]
    leisure_templates: tuple[str, ...]
    departure_templates: tuple[str, ...]


_COUNTRY_ADJECTIVE = {
    "Norway": "Norwegian",
    "Sweden": "Swedish",
    "Finland": "Finnish",
    "Denmark": "Danish",
    "Iceland": "Icelandic",
}

_IDENTITY_OVERRIDES: dict[str, str] = {
    "Oslo": "the Norwegian capital",
    "Bergen": "this historic harbour city and fjord gateway",
    "Stavanger": "Norway’s fjord gateway and old wooden city",
    "Kristiansand": "Southern Norway’s coastal city",
    "Tromsø": "Norway’s Arctic capital",
    "Trondheim": "this historic fjordside city",
    "Ålesund": "this Art Nouveau coastal city",
    "Flåm": "this fjord village beneath the mountains",
    "Voss": "this mountain village between fjords and valleys",
    "Geiranger": "this village at the heart of Geirangerfjord",
    "Reine": "this Lofoten fishing village beneath dramatic peaks",
    "Svolvær": "this Lofoten harbour town",
    "Longyearbyen": "this High Arctic settlement in Svalbard",
    "Stockholm": "Sweden’s island capital",
    "Gothenburg": "Sweden’s west-coast harbour city",
    "Malmö": "this southern Swedish city by the Øresund",
    "Kiruna": "this Swedish Lapland gateway",
    "Abisko": "this Arctic national-park village",
    "Åre": "this Swedish mountain village",
    "Visby": "this medieval Baltic island town",
    "Helsinki": "Finland’s design-minded waterfront capital",
    "Rovaniemi": "this Lapland city on the Arctic Circle",
    "Turku": "Finland’s riverside archipelago gateway",
    "Tampere": "this Finnish lakeland city",
    "Levi": "this Finnish Lapland fell resort",
    "Saariselkä": "this Arctic fell village",
    "Porvoo": "this riverside town of old wooden streets",
    "Åland": "this calm Nordic archipelago",
    "Copenhagen": "the Danish capital of design, canals and harbour life",
    "Aarhus": "this Jutland city of culture and waterfront life",
    "Odense": "this Funen city of fairytale heritage",
    "Aalborg": "this North Jutland harbour city",
    "Billund": "this family-friendly Jutland gateway",
    "Roskilde": "this Viking city by the fjord",
    "Helsingør": "this castle town by the Øresund",
    "Skagen": "this northern Danish seaside town",
    "Bornholm": "this Baltic island of villages and coastline",
    "Reykjavík": "Iceland’s compact coastal capital",
    "Keflavík": "this Reykjanes arrival gateway",
    "Blue Lagoon": "this geothermal lagoon in the lava fields",
    "Golden Circle": "Iceland’s classic waterfall, geyser and national-park route",
    "South Coast": "Iceland’s waterfall, glacier and black-sand coast",
    "Vík": "this South Iceland village by the black-sand coast",
    "Jökulsárlón": "this glacier lagoon of drifting icebergs",
    "Skaftafell": "this Vatnajökull national-park landscape",
    "Vatnajökull": "this vast Icelandic glacier wilderness",
    "Akureyri": "North Iceland’s fjordside capital",
    "Mývatn": "this volcanic lake landscape in North Iceland",
    "Húsavík": "this North Iceland whale-watching harbour",
    "Snæfellsnes": "this peninsula of coastal villages and volcanic scenery",
    "Ísafjörður": "this Westfjords harbour town beneath the mountains",
    "Westfjords": "Iceland’s remote fjords and dramatic coast",
    "Landmannalaugar": "this highland area of colourful rhyolite mountains",
    "Ring Road": "Iceland’s full scenic circuit",
}

_ATMOSPHERE_OVERRIDES: dict[str, tuple[str, ...]] = {
    "Oslo": (
        "the harbourfront and waterfront neighbourhoods",
        "museums, galleries and modern Nordic architecture",
        "capital streets, green city spaces and fjordside cafés",
    ),
    "Bergen": (
        "Bryggen and the harbourfront",
        "colourful wooden streets and hillside viewpoints",
        "Fløyen views, local cafés and fjord-gateway atmosphere",
    ),
    "Stavanger": (
        "the harbourfront and old wooden streets",
        "local cafés around the centre",
        "an easy evening in Norway’s fjord gateway",
    ),
    "Kristiansand": (
        "the harbourfront and southern coastal streets",
        "time by the sea",
        "local cafés in Southern Norway’s coastal city",
    ),
    "Tromsø": (
        "Arctic waterfront views",
        "northern cafés and compact city streets",
        "mountain scenery around the city",
    ),
    "Rovaniemi": (
        "riverside paths and Lapland atmosphere",
        "northern design shops and local cafés",
        "time to settle into the Arctic Circle setting",
    ),
    "Copenhagen": (
        "canals, harbour baths and waterfront streets",
        "design shops, cafés and historic squares",
        "neighbourhood life around the Danish capital",
    ),
    "Stockholm": (
        "island viewpoints and waterfront walks",
        "Gamla Stan, museums and local cafés",
        "harbour life across the Swedish capital",
    ),
    "Helsinki": (
        "waterfront markets and design districts",
        "harbour views, architecture and local cafés",
        "easy walks through Finland’s capital",
    ),
    "Reykjavík": (
        "colourful streets and coastal viewpoints",
        "local cafés, galleries and harbour life",
        "time to settle into Iceland’s capital",
    ),
}

_PROFILE_ATMOSPHERE: dict[str, tuple[str, ...]] = {
    "coastal_city": ("the harbourfront", "coastal streets and viewpoints", "waterfront cafés and small shops"),
    "urban_culture": ("historic streets", "museums, galleries or design shops", "local cafés and city viewpoints"),
    "arctic": ("Arctic scenery", "local cafés and a slower northern pace", "the waterfront or village centre"),
    "scenic_nature": ("nearby viewpoints", "village streets or waterside paths", "the surrounding fjord, lake or valley scenery"),
    "mountain_resort": ("mountain views around the resort", "local cafés and resort village atmosphere", "time between outdoor experiences"),
    "national_park": ("viewpoints and visitor areas", "trails and surrounding landscapes", "a calm pause between nature experiences"),
    "scenic_route": ("scenic stops along the route", "viewpoints and short photo pauses", "the changing landscapes"),
    "icelandic_town": ("the town centre and harbour area", "local cafés and Icelandic village life", "nearby coastal or lava-field views"),
    "icelandic_nature": ("viewpoints and wide-open landscapes", "short scenic pauses", "the surrounding volcanic scenery"),
    "icelandic_landmark": ("viewpoints around the landmark", "time for photos and surrounding scenery", "a relaxed pause before continuing the route"),
    "thermal_lagoon": ("time to slow down in the geothermal setting", "nearby lava-field views", "a calm pause before continuing the journey"),
    "destination": ("local streets and viewpoints", "small local stops", "the surrounding scenery"),
}

_PROFILE_HOOKS: dict[str, tuple[str, ...]] = {
    "coastal_city": ("harbour", "coast", "waterfront"),
    "urban_culture": ("culture", "architecture", "local neighbourhoods"),
    "arctic": ("Arctic setting", "northern light", "winter landscapes"),
    "scenic_nature": ("fjord scenery", "mountain views", "village atmosphere"),
    "mountain_resort": ("mountain scenery", "outdoor life", "resort atmosphere"),
    "national_park": ("protected landscapes", "viewpoints", "trails"),
    "scenic_route": ("changing landscapes", "route highlights", "photo stops"),
    "icelandic_town": ("harbour", "coast", "local Icelandic life"),
    "icelandic_nature": ("volcanic scenery", "wide-open landscapes", "waterfalls or glaciers"),
    "icelandic_landmark": ("landmark scenery", "viewpoints", "weather-shaped landscapes"),
    "thermal_lagoon": ("geothermal water", "lava fields", "slow travel"),
    "destination": ("local character", "scenery", "independent time"),
}

_ARRIVAL_TEMPLATES = (
    "After check-in, the rest of the day is yours to settle in, relax, and enjoy your first impressions of {identity}.",
    "Once settled, keep the rest of the day relaxed, with time to get a first feel for {identity}.",
    "After check-in, the day stays unhurried so you can settle in and begin getting a sense of {identity}.",
)

_LEISURE_TEMPLATES = (
    "Use the remaining time in {city} at your own pace, whether you prefer {focus}.",
    "Use the remaining time in {city} flexibly, with space for {focus}.",
    "Use the remaining time in {city} unhurriedly, leaving room for {focus}.",
)

_DEPARTURE_TEMPLATES = (
    "After check-out, say farewell to {identity} before continuing your onward journey.",
    "Your time in {city} comes to a close today, with departure arrangements kept simple after check-out.",
)


def _adjective(country: str) -> str:
    return _COUNTRY_ADJECTIVE.get(country, str(country or "local").strip() or "local")


def _clean_region(region: str) -> str:
    return re.sub(r"\s+", " ", str(region or "").strip())


def _identity_for(record: NordicDestination | None, fallback_name: str = "") -> str:
    if record and record.name in _IDENTITY_OVERRIDES:
        return _IDENTITY_OVERRIDES[record.name]
    name = record.name if record else polish_title(fallback_name)
    if not record:
        return "this place" if not name else f"{name} and its local setting"

    country_adj = _adjective(record.country)
    profile = record.copy_profile or "destination"
    kind = record.destination_type or "destination"
    region = _clean_region(record.region)

    if profile == "arctic":
        return f"this Arctic {country_adj} destination"
    if profile == "coastal_city":
        if kind in {"city", "town"}:
            return f"this {country_adj} coastal city"
        if kind == "island":
            return f"this {country_adj} island destination"
        return f"this {country_adj} coastal destination"
    if profile == "scenic_nature":
        if "fjord" in region.lower() or kind == "fjord":
            return f"this {country_adj} fjordland destination"
        if kind == "village":
            return f"this scenic {country_adj} village"
        return f"this {country_adj} nature destination"
    if profile == "mountain_resort":
        return f"this {country_adj} mountain resort"
    if profile == "national_park":
        return f"this {country_adj} national-park landscape"
    if profile == "scenic_route":
        return f"this signature {country_adj} scenic route"
    if profile == "thermal_lagoon":
        return "this geothermal Icelandic lagoon"
    if profile == "icelandic_town":
        return "this Icelandic town and coastal setting"
    if profile == "icelandic_nature":
        return "this Icelandic landscape"
    if profile == "icelandic_landmark":
        return "this Icelandic landmark setting"
    if profile == "urban_culture":
        if kind in {"city", "town"}:
            return f"this {country_adj} city"
        return f"this {country_adj} cultural destination"
    if region and region.lower() != record.country.lower():
        return f"this {region} destination"
    return f"this {country_adj} destination"


def _profile_atmosphere(record: NordicDestination | None) -> tuple[str, ...]:
    if record and record.name in _ATMOSPHERE_OVERRIDES:
        return _ATMOSPHERE_OVERRIDES[record.name]
    profile = record.copy_profile if record else "destination"
    atmosphere = _PROFILE_ATMOSPHERE.get(profile, _PROFILE_ATMOSPHERE["destination"])
    if not record:
        return atmosphere
    region = _clean_region(record.region)
    country_adj = _adjective(record.country).lower()
    regional_phrase = f"{region} atmosphere" if region and region != record.country else f"{country_adj} local character"
    return tuple(dict.fromkeys((*atmosphere, regional_phrase)))


def _profile_hooks(record: NordicDestination | None) -> tuple[str, ...]:
    profile = record.copy_profile if record else "destination"
    hooks = _PROFILE_HOOKS.get(profile, _PROFILE_HOOKS["destination"])
    if not record:
        return hooks
    return tuple(dict.fromkeys((*hooks, record.region, record.country)))


def _record_for(value: object) -> NordicDestination | None:
    record = destination_for_alias(value)
    if record:
        return record
    text = polish_title(str(value or "").strip())
    return destination_for_alias(text) if text else None


def _fallback_profile(value: object = "") -> DestinationProfile:
    name = polish_title(str(value or "").strip())
    return DestinationProfile(
        name=name,
        country="",
        region="",
        destination_type="destination",
        copy_profile="destination",
        aliases=(),
        identity=_identity_for(None, name),
        arrival_identity=_identity_for(None, name),
        leisure_identity=name or "the area",
        atmosphere=_PROFILE_ATMOSPHERE["destination"],
        hooks=_PROFILE_HOOKS["destination"],
        arrival_templates=_ARRIVAL_TEMPLATES,
        leisure_templates=_LEISURE_TEMPLATES,
        departure_templates=_DEPARTURE_TEMPLATES,
    )


def _profile_from_record(record: NordicDestination) -> DestinationProfile:
    identity = _identity_for(record)
    return DestinationProfile(
        name=record.name,
        country=record.country,
        region=record.region,
        destination_type=record.destination_type,
        copy_profile=record.copy_profile,
        aliases=record.aliases,
        identity=identity,
        arrival_identity=identity,
        leisure_identity=record.name,
        atmosphere=_profile_atmosphere(record),
        hooks=_profile_hooks(record),
        arrival_templates=_ARRIVAL_TEMPLATES,
        leisure_templates=_LEISURE_TEMPLATES,
        departure_templates=_DEPARTURE_TEMPLATES,
    )


@lru_cache(maxsize=1)
def destination_profiles() -> dict[str, DestinationProfile]:
    """Return profiles for every registered Nordic travel destination."""

    return {record.name: _profile_from_record(record) for record in travel_destination_records()}


def destination_profile_for(value: object) -> DestinationProfile:
    record = _record_for(value)
    if not record:
        return _fallback_profile(value)
    return destination_profiles().get(record.name) or _profile_from_record(record)


def is_known_destination(value: object) -> bool:
    return _record_for(value) is not None


def destination_identity(value: object) -> str:
    return destination_profile_for(value).identity


def _rows_text(rows: Iterable[Mapping[str, object]] | None) -> str:
    parts: list[str] = []
    for row in rows or []:
        if not isinstance(row, Mapping):
            continue
        parts.extend(
            str(row.get(key, "") or "")
            for key in ("day", "city", "title", "original_title", "details", "description")
        )
    return " ".join(parts).lower()


def stable_variant_index(*parts: object, count: int) -> int:
    if count <= 1:
        return 0
    payload = "|".join(str(part or "") for part in parts)
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % count


def select_arrival_sentence(city: object, rows: Iterable[Mapping[str, object]] | None = None) -> str:
    profile = destination_profile_for(city)
    idx = stable_variant_index(profile.name, _rows_text(rows), "arrival", count=len(profile.arrival_templates))
    return profile.arrival_templates[idx].format(city=profile.name, identity=profile.arrival_identity)


def _format_focus(options: Sequence[str]) -> str:
    clean = [re.sub(r"\s+", " ", str(option or "").strip()) for option in options if str(option or "").strip()]
    clean = list(dict.fromkeys(clean))
    if not clean:
        return "local streets, viewpoints, and the surrounding scenery"
    if len(clean) == 1:
        return clean[0]
    if len(clean) == 2:
        return f"{clean[0]} or {clean[1]}"
    return f"{clean[0]}, {clean[1]}, or {clean[2]}"


def _rotate(values: Sequence[str], seed: str) -> list[str]:
    items = list(values)
    if len(items) <= 1:
        return items
    offset = stable_variant_index(seed, count=len(items))
    return items[offset:] + items[:offset]


def destination_leisure_sentence(
    value: object,
    rows: Iterable[Mapping[str, object]] | None = None,
    options: Sequence[str] | None = None,
) -> str:
    profile = destination_profile_for(value)
    city = profile.name or polish_title(str(value or "").strip())
    if not city:
        return "Use the remaining time at your own pace, with room to relax, explore independently, or settle into the day."

    context = _rows_text(rows)
    source_options = tuple(options or profile.atmosphere)
    rotated = _rotate(source_options, f"{city}|{context}|leisure")
    selected = rotated[:3]
    focus = _format_focus(selected)
    template_idx = stable_variant_index(city, context, "leisure-template", count=len(profile.leisure_templates))
    return profile.leisure_templates[template_idx].format(city=city, identity=profile.identity, focus=focus)


def _is_return_visit(visit_context: object | None) -> bool:
    return bool(getattr(visit_context, "is_return_visit", False))


def destination_arrival_intro(
    city: object,
    transfer_phrase: str,
    detail_level: str,
    *,
    display_destination: str | None = None,
    rows: Iterable[Mapping[str, object]] | None = None,
    visit_context: object | None = None,
) -> str:
    destination = str(display_destination or "").strip() or destination_profile_for(city).name or polish_title(str(city or "").strip()) or "this place"
    transfer_phrase = re.sub(r"\s+", " ", str(transfer_phrase or "").strip())
    transfer_phrase = transfer_phrase or "After arrival, make your way to your accommodation."
    return_visit = _is_return_visit(visit_context)
    if detail_level == "Elegant concise":
        prefix = "Return to" if return_visit else "Welcome to"
        return f"{prefix} {destination}. {transfer_phrase}"

    if return_visit:
        profile = destination_profile_for(city)
        identity = profile.arrival_identity or profile.identity or destination
        arrival_sentence = f"Back in {identity}, the rest of the day is kept relaxed after check-in, with time to settle back into familiar surroundings."
    elif destination.casefold() != str(city or "").strip().casefold() and destination:
        identity = destination
        arrival_sentence = f"After check-in, the rest of the day is yours to settle in, relax, and enjoy your first impressions of {identity}."
    else:
        arrival_sentence = select_arrival_sentence(city, rows)

    connector = "Once settled," if "check in" in transfer_phrase.casefold() or "check-in" in transfer_phrase.casefold() else "After check-in,"
    if arrival_sentence.startswith("After check-in,") and connector != "After check-in,":
        arrival_sentence = connector + arrival_sentence[len("After check-in,"):]
        arrival_sentence = arrival_sentence.replace(
            "the rest of the day is yours to settle in, relax, and enjoy",
            "the rest of the day is yours to relax and enjoy",
        )
    prefix = "Return to" if return_visit else "Welcome to"
    return f"{prefix} {destination}. {transfer_phrase} {arrival_sentence}"


def destination_stay_intro(
    city: object,
    detail_level: str,
    rows: Iterable[Mapping[str, object]] | None = None,
    *,
    visit_context: object | None = None,
) -> str:
    destination = destination_profile_for(city).name or polish_title(str(city or "").strip()) or "this place"
    return_visit = _is_return_visit(visit_context)
    if detail_level == "Elegant concise":
        if return_visit:
            return f"Return to {destination}. Time is kept relaxed after arrival so you can settle back in."
        return f"Welcome to {destination}. Time is kept relaxed after arrival so you can settle in."
    if return_visit:
        profile = destination_profile_for(city)
        identity = profile.arrival_identity or profile.identity or destination
        return f"Return to {destination}. After arrival, the day is kept relaxed so you can check in and settle back into your accommodation. Back in {identity}, use the remaining time at your own pace."
    arrival_sentence = select_arrival_sentence(city, rows)
    return f"Welcome to {destination}. After arrival, the day is kept relaxed so you can check in and settle into your accommodation. {arrival_sentence}"


__all__ = [
    "DestinationProfile",
    "destination_arrival_intro",
    "destination_identity",
    "destination_leisure_sentence",
    "destination_profile_for",
    "destination_profiles",
    "destination_stay_intro",
    "is_known_destination",
    "select_arrival_sentence",
    "stable_variant_index",
]

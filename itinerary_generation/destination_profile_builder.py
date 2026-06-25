"""Registry lookup and construction of destination profiles."""

from __future__ import annotations

from functools import lru_cache
import re

from itinerary_generation.destination_profile_data import (
    ARRIVAL_TEMPLATES, ATMOSPHERE_OVERRIDES, COUNTRY_ADJECTIVE,
    DEPARTURE_TEMPLATES, IDENTITY_OVERRIDES, LEISURE_TEMPLATES,
    PROFILE_ATMOSPHERE, PROFILE_HOOKS,
)
from itinerary_generation.destination_profile_model import DestinationProfile
from itinerary_generation.destination_registry import NordicDestination, destination_for_alias, travel_destination_records
from text_polish import polish_title


def _adjective(country: str) -> str:
    return COUNTRY_ADJECTIVE.get(country, str(country or "local").strip() or "local")


def _clean_region(region: str) -> str:
    return re.sub(r"\s+", " ", str(region or "").strip())


def _identity_for(record: NordicDestination | None, fallback_name: str = "") -> str:
    if record and record.name in IDENTITY_OVERRIDES:
        return IDENTITY_OVERRIDES[record.name]
    name = record.name if record else polish_title(fallback_name)
    if not record:
        return "this place" if not name else f"{name} and its local setting"
    country_adj = _adjective(record.country)
    profile, kind, region = record.copy_profile or "destination", record.destination_type or "destination", _clean_region(record.region)
    if profile == "arctic": return f"this Arctic {country_adj} destination"
    if profile == "coastal_city":
        if kind in {"city", "town"}: return f"this {country_adj} coastal city"
        if kind == "island": return f"this {country_adj} island destination"
        return f"this {country_adj} coastal destination"
    if profile == "scenic_nature":
        if "fjord" in region.lower() or kind == "fjord": return f"this {country_adj} fjordland destination"
        if kind == "village": return f"this scenic {country_adj} village"
        return f"this {country_adj} nature destination"
    identities = {
        "mountain_resort": f"this {country_adj} mountain resort", "national_park": f"this {country_adj} national-park landscape",
        "scenic_route": f"this signature {country_adj} scenic route", "thermal_lagoon": "this geothermal Icelandic lagoon",
        "icelandic_town": "this Icelandic town and coastal setting", "icelandic_nature": "this Icelandic landscape",
        "icelandic_landmark": "this Icelandic landmark setting",
    }
    if profile in identities: return identities[profile]
    if profile == "urban_culture": return f"this {country_adj} city" if kind in {"city", "town"} else f"this {country_adj} cultural destination"
    if region and region.lower() != record.country.lower(): return f"this {region} destination"
    return f"this {country_adj} destination"


def _profile_atmosphere(record: NordicDestination | None) -> tuple[str, ...]:
    if record and record.name in ATMOSPHERE_OVERRIDES: return ATMOSPHERE_OVERRIDES[record.name]
    atmosphere = PROFILE_ATMOSPHERE.get(record.copy_profile if record else "destination", PROFILE_ATMOSPHERE["destination"])
    if not record: return atmosphere
    region = _clean_region(record.region)
    regional_phrase = f"{region} atmosphere" if region and region != record.country else f"{_adjective(record.country).lower()} local character"
    return tuple(dict.fromkeys((*atmosphere, regional_phrase)))


def _profile_hooks(record: NordicDestination | None) -> tuple[str, ...]:
    hooks = PROFILE_HOOKS.get(record.copy_profile if record else "destination", PROFILE_HOOKS["destination"])
    return hooks if not record else tuple(dict.fromkeys((*hooks, record.region, record.country)))


def _profile(record: NordicDestination | None, fallback: object = "") -> DestinationProfile:
    name = record.name if record else polish_title(str(fallback or "").strip())
    identity = _identity_for(record, name)
    return DestinationProfile(
        name=name, country=record.country if record else "", region=record.region if record else "",
        destination_type=record.destination_type if record else "destination", copy_profile=record.copy_profile if record else "destination",
        aliases=record.aliases if record else (), identity=identity, arrival_identity=identity,
        leisure_identity=name or "the area", atmosphere=_profile_atmosphere(record), hooks=_profile_hooks(record),
        arrival_templates=ARRIVAL_TEMPLATES, leisure_templates=LEISURE_TEMPLATES, departure_templates=DEPARTURE_TEMPLATES,
    )


def _record_for(value: object) -> NordicDestination | None:
    record = destination_for_alias(value)
    text = polish_title(str(value or "").strip())
    return record or (destination_for_alias(text) if text else None)


@lru_cache(maxsize=1)
def destination_profiles() -> dict[str, DestinationProfile]:
    return {record.name: _profile(record) for record in travel_destination_records()}


def destination_profile_for(value: object) -> DestinationProfile:
    record = _record_for(value)
    return destination_profiles().get(record.name) or _profile(record) if record else _profile(None, value)


def is_known_destination(value: object) -> bool:
    return _record_for(value) is not None


def destination_identity(value: object) -> str:
    return destination_profile_for(value).identity

"""Arrival-focus content for destination records."""
from __future__ import annotations

from itinerary_generation.destination_registry import NordicDestination
from itinerary_generation.destination_seasonal_variants import destination_copy_profile

ARRIVAL_FOCUS_BY_PROFILE: dict[str, str] = {
    "coastal_city": "coastal setting and harbour atmosphere",
    "urban_culture": "city culture and local neighbourhoods",
    "arctic": "Arctic landscapes and northern atmosphere",
    "scenic_nature": "surrounding scenery and natural setting",
    "mountain_resort": "mountain scenery and resort atmosphere",
    "national_park": "national park landscapes",
    "scenic_route": "scenic route setting",
    "icelandic_town": "Icelandic landscapes and local life",
    "icelandic_nature": "dramatic Icelandic nature",
    "icelandic_landmark": "landmark scenery",
    "thermal_lagoon": "geothermal landscape",
    "destination": "regional character and local scenery",
}


COUNTRY_STYLE_HINTS: dict[str, str] = {
    "Norway": "Norwegian",
    "Sweden": "Swedish",
    "Finland": "Finnish",
    "Denmark": "Danish",
    "Iceland": "Icelandic",
}


def arrival_focus_for_destination(record: NordicDestination | None) -> str:
    profile = destination_copy_profile(record)
    focus = ARRIVAL_FOCUS_BY_PROFILE.get(profile, ARRIVAL_FOCUS_BY_PROFILE["destination"])
    if record and profile == "destination" and record.country in COUNTRY_STYLE_HINTS:
        return f"{COUNTRY_STYLE_HINTS[record.country].lower()} character and local scenery"
    return focus


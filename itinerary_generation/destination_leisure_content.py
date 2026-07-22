"""Destination leisure options, filtering, and final prose."""
from __future__ import annotations

from typing import Iterable, Sequence

from itinerary_generation.destination_content_lookup import resolve_destination
from itinerary_generation.destination_profiles import destination_leisure_sentence
from itinerary_generation.destination_registry import NordicDestination
from itinerary_generation.destination_seasonal_variants import destination_copy_profile

LEISURE_OVERRIDES: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "Oslo": (
        ("waterfront neighbourhoods", ("fjord sightseeing", "oslofjord", "fjord cruise")),
        ("museums, galleries and modern Nordic architecture", ("museum", "gallery", "city tour")),
        ("capital streets, green city spaces and fjordside cafés", ("food tour", "culinary", "tasting")),
    ),
    "Kristiansand": (
        ("the harbourfront and southern coastal streets", ("harbour", "harbor")),
        ("time by the sea", ("walking tour", "city walk")),
        ("local cafés in Southern Norway’s coastal city", ("kayak", "kayaking", "otra river")),
    ),
    "Stavanger": (
        ("the harbourfront and old wooden streets", ("harbour", "harbor", "cruise")),
        ("an easy evening in Norway’s fjord gateway", ("walking tour", "city walk")),
        ("local cafés around the centre", ("food", "culinary", "tasting")),
    ),
    "Bergen": (
        ("Bryggen and the harbourfront", ("harbour", "harbor", "cruise")),
        ("colourful wooden streets and hillside viewpoints", ("walking tour", "bergen past")),
        ("Fløyen views, local cafés and fjord-gateway atmosphere", ("fløy", "floy", "funicular", "fløibanen", "floibanen")),
    ),
    "Flåm": (
        ("fjordside paths", ("fjord cruise", "boat")),
        ("railway views and village corners", ("railway", "train", "flåm railway", "flam railway")),
        ("time beside the fjord", ("kayak", "hike")),
    ),
    "Geiranger": (
        ("fjord viewpoints", ("fjord cruise", "viewpoint")),
        ("village paths by the water", ("walking", "guided")),
        ("time to take in the surrounding mountains", ("hike", "waterfall")),
    ),
    "Vík": (
        ("views towards the black-sand coast", ("reynisfjara", "black sand", "beach")),
        ("the village centre and coastal viewpoints", ("walking", "guided")),
        ("time to absorb the South Coast scenery", ("waterfall", "glacier")),
    ),
    "Rovaniemi": (
        ("riverside paths and Lapland atmosphere", ("santa", "arctic circle")),
        ("local cafés and northern design shops", ("food", "tasting")),
        ("time to settle into the forested Arctic setting", ("reindeer", "husky", "aurora", "northern lights")),
    ),
}

LEISURE_BY_PROFILE: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "coastal_city": (
        ("the harbourfront", ("harbour", "harbor", "cruise", "port")),
        ("coastal streets and viewpoints", ("walking tour", "city walk", "guided walk")),
        ("local cafés and small shops", ("food", "culinary", "tasting", "market")),
        ("time by the water", ("fjord cruise", "boat", "kayak", "ferry")),
    ),
    "urban_culture": (
        ("the city centre", ("walking tour", "city tour", "old town")),
        ("local cafés and neighbourhood streets", ("food", "culinary", "tasting")),
        ("museums, galleries or design shops", ("museum", "gallery", "design")),
        ("waterfront viewpoints", ("boat", "cruise", "harbour", "harbor")),
    ),
    "arctic": (
        ("Arctic scenery around town", ("northern lights", "aurora", "fjord", "viewpoint")),
        ("local cafés and a slower northern pace", ("food", "tasting", "market")),
        ("the waterfront or village centre", ("walking tour", "city walk")),
        ("time to settle into the northern atmosphere", ("reindeer", "husky", "sami", "sámi")),
    ),
    "scenic_nature": (
        ("nearby viewpoints", ("viewpoint", "funicular", "cable car")),
        ("village streets or waterside paths", ("walking tour", "guided walk")),
        ("the surrounding fjord, lake or valley scenery", ("fjord cruise", "boat", "kayak", "hike")),
        ("local cafés or a relaxed pause between journeys", ("food", "culinary", "tasting")),
    ),
    "mountain_resort": (
        ("mountain views around the resort", ("hike", "ski", "snowshoe", "gondola")),
        ("local cafés and resort village atmosphere", ("food", "tasting")),
        ("time to rest between outdoor experiences", ("reindeer", "husky", "aurora", "northern lights")),
    ),
    "national_park": (
        ("viewpoints and visitor areas", ("hike", "guided walk", "trail")),
        ("time to take in the surrounding landscapes", ("glacier", "waterfall", "fjord", "canyon")),
        ("a calm pause between nature experiences", ("activity", "tour")),
    ),
    "scenic_route": (
        ("scenic stops along the route", ("guided", "tour", "transfer")),
        ("viewpoints and short photo pauses", ("photo", "viewpoint")),
        ("time to enjoy the changing landscapes", ("train", "coach", "cruise", "ferry")),
    ),
    "icelandic_town": (
        ("the town centre and harbour area", ("walking tour", "harbour", "harbor")),
        ("local cafés and Icelandic village life", ("food", "tasting")),
        ("nearby coastal or lava-field views", ("lava", "coast", "viewpoint")),
    ),
    "icelandic_nature": (
        ("viewpoints and wide-open landscapes", ("hike", "guided", "glacier", "waterfall")),
        ("short scenic pauses between experiences", ("tour", "activity")),
        ("time to absorb the surrounding volcanic scenery", ("lava", "crater", "geothermal")),
    ),
    "icelandic_landmark": (
        ("viewpoints around the landmark", ("guided", "tour", "hike")),
        ("time for photos and the surrounding scenery", ("photo", "viewpoint")),
        ("a relaxed pause before continuing the route", ("transfer", "drive")),
    ),
    "thermal_lagoon": (
        ("time to slow down in the geothermal setting", ("lagoon", "spa", "wellness")),
        ("nearby lava-field views", ("lava", "reykjanes")),
        ("a calm pause before continuing the journey", ("transfer", "flight")),
    ),
    "destination": (
        ("local streets and viewpoints", ("walking tour", "guided walk")),
        ("cafés or small local stops", ("food", "tasting")),
        ("the surrounding scenery", ("nature", "viewpoint", "boat", "hike")),
    ),
}


def _rows_text(rows: Iterable[dict] | None) -> str:
    return " ".join(
        " ".join(
            str(row.get(key, "") or "")
            for key in ("day", "city", "title", "original_title", "details", "description")
        )
        for row in rows or []
        if isinstance(row, dict)
    ).lower()



def leisure_options_for(name: str, record: NordicDestination | None):
    profile = destination_copy_profile(record)
    return LEISURE_OVERRIDES.get(name, LEISURE_BY_PROFILE.get(profile, LEISURE_BY_PROFILE["destination"]))

def _choose_leisure_options(options: Sequence[tuple[str, tuple[str, ...]]], context: str) -> list[str]:
    chosen: list[str] = []
    for phrase, covered_markers in options:
        if any(marker in context for marker in covered_markers):
            continue
        if phrase not in chosen:
            chosen.append(phrase)
        if len(chosen) >= 3:
            break
    if chosen:
        return chosen
    for phrase, _markers in options:
        if phrase not in chosen:
            chosen.append(phrase)
        if len(chosen) >= 2:
            break
    return chosen or ["local streets", "cafés", "the surrounding scenery"]


def leisure_description(value: object, rows: Sequence[dict] | Iterable[dict] | None = None) -> str:
    """Return destination-aware free-time copy without repeating covered activities."""

    record = resolve_destination(value).record
    name = record.name if record else resolve_destination(value).name
    if not name:
        return "Open time today is left flexible, with room to relax, explore independently, or settle into the day."

    context = _rows_text(rows)
    options = _choose_leisure_options(leisure_options_for(name, record), context)
    return destination_leisure_sentence(name, rows, options)


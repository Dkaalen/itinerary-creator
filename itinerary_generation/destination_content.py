"""Premium destination copy generated from the Nordic registry.

The registry contains hundreds of Nordic itinerary places.  This module turns
those structured profiles into deterministic, client-facing fallback copy so
empty supplier rows never collapse into generic wording such as "time at
leisure".  It does not invent itinerary facts; it only gives light destination
colour when the source input is intentionally sparse.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Sequence

from itinerary_generation.destination_registry import NordicDestination, destination_for_alias
from itinerary_generation.destination_profiles import destination_leisure_sentence
from text_polish import polish_title


@dataclass(frozen=True)
class DestinationCopy:
    arc: str
    leisure_options: tuple[tuple[str, tuple[str, ...]], ...]
    arrival_focus: str


CAPITAL_OVERRIDES: dict[str, str] = {
    "Oslo": "Discover the Norwegian capital",
    "Stockholm": "Stockholm islands and old town",
    "Copenhagen": "Copenhagen design and harbour life",
    "Helsinki": "Helsinki design and waterfront life",
    "Reykjavík": "Reykjavík culture and coastal colour",
}

DESTINATION_ARC_OVERRIDES: dict[str, str] = {
    **CAPITAL_OVERRIDES,
    "Kristiansand": "Southern coastal charm",
    "Stavanger": "Stavanger harbour and fjord gateway",
    "Bergen": "Bergen harbour and mountain views",
    "Tromsø": "Arctic city and northern landscapes",
    "Alta": "Arctic nature and Northern Lights country",
    "Rovaniemi": "Lapland forest and Arctic Circle atmosphere",
    "Flåm": "Fjord village and railway scenery",
    "Voss": "Mountain village and fjordland adventure",
    "Geiranger": "Geirangerfjord views and village atmosphere",
    "Ålesund": "Art Nouveau streets and coastal views",
    "Svolvær": "Lofoten harbour and mountain scenery",
    "Reine": "Lofoten fishing village and dramatic peaks",
    "Trondheim": "Historic Trondheim and fjordside streets",
    "Kiruna": "Swedish Lapland and Arctic landscapes",
    "Abisko": "Arctic national park and mountain views",
    "Åre": "Mountain village and alpine scenery",
    "Visby": "Medieval walls and Baltic island atmosphere",
    "Gothenburg": "Gothenburg canals and coastal culture",
    "Malmö": "Modern city life and Öresund connections",
    "Turku": "Archipelago gateway and riverside history",
    "Tampere": "Lakeland city and industrial heritage",
    "Levi": "Lapland resort and fell scenery",
    "Saariselkä": "Arctic fells and wilderness atmosphere",
    "Porvoo": "Old wooden streets and riverside charm",
    "Åland": "Archipelago islands and maritime calm",
    "Aarhus": "Jutland culture and waterfront city life",
    "Odense": "Fairytale heritage and Funen charm",
    "Aalborg": "North Jutland harbour and city culture",
    "Billund": "Family-friendly Jutland gateway",
    "Roskilde": "Viking heritage and fjord views",
    "Helsingør": "Castle town and Øresund views",
    "Skagen": "Northern light and seaside atmosphere",
    "Bornholm": "Baltic island villages and coastal scenery",
    "Keflavík": "Reykjanes coast and arrival gateway",
    "Blue Lagoon": "Geothermal lagoon and Reykjanes lava fields",
    "Golden Circle": "Iceland’s classic waterfall and geyser route",
    "South Coast": "Waterfalls, black sands and glacier views",
    "Vík": "Black-sand coast and South Iceland scenery",
    "Jökulsárlón": "Glacier lagoon and floating icebergs",
    "Skaftafell": "Glacier landscapes and national park trails",
    "Vatnajökull": "Glacier wilderness and volcanic landscapes",
    "Akureyri": "North Iceland culture and fjord setting",
    "Mývatn": "Volcanic lake landscapes and geothermal scenery",
    "Húsavík": "Whale-watching harbour and North Iceland coast",
    "Snæfellsnes": "Peninsula scenery and coastal villages",
    "Ísafjörður": "Westfjords harbour and mountain setting",
    "Westfjords": "Remote fjords and dramatic coastal scenery",
    "Landmannalaugar": "Highland colours and rhyolite mountains",
    "Ring Road": "Iceland’s full scenic circuit",
}

PROFILE_ARC_TEMPLATES: dict[str, str] = {
    "coastal_city": "{name} coastal character and harbour life",
    "urban_culture": "{name} culture and city life",
    "arctic": "{name} Arctic landscapes and northern atmosphere",
    "scenic_nature": "{name} scenery and local nature",
    "mountain_resort": "{name} mountain scenery and resort atmosphere",
    "national_park": "{name} national park landscapes",
    "scenic_route": "{name} scenic route",
    "icelandic_town": "{name} Icelandic landscapes and local life",
    "icelandic_nature": "{name} dramatic Icelandic nature",
    "icelandic_landmark": "{name} Icelandic landmark scenery",
    "thermal_lagoon": "{name} geothermal lagoon experience",
    "destination": "{name} regional character and local scenery",
}

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

COUNTRY_STYLE_HINTS: dict[str, str] = {
    "Norway": "Norwegian",
    "Sweden": "Swedish",
    "Finland": "Finnish",
    "Denmark": "Danish",
    "Iceland": "Icelandic",
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


def _record_for(value: object) -> NordicDestination | None:
    record = destination_for_alias(value)
    if record:
        return record
    text = polish_title(str(value or "").strip())
    return destination_for_alias(text) if text else None


def _display_name(value: object, record: NordicDestination | None) -> str:
    return record.name if record else polish_title(str(value or "").strip())


def _profile(record: NordicDestination | None) -> str:
    return record.copy_profile if record and record.copy_profile else "destination"


def _arc_for_record(name: str, record: NordicDestination | None) -> str:
    if record and record.name in DESTINATION_ARC_OVERRIDES:
        return DESTINATION_ARC_OVERRIDES[record.name]
    if name in DESTINATION_ARC_OVERRIDES:
        return DESTINATION_ARC_OVERRIDES[name]
    profile = _profile(record)
    template = PROFILE_ARC_TEMPLATES.get(profile, PROFILE_ARC_TEMPLATES["destination"])
    return template.format(name=name)


def _arrival_focus_for_record(record: NordicDestination | None) -> str:
    profile = _profile(record)
    focus = ARRIVAL_FOCUS_BY_PROFILE.get(profile, ARRIVAL_FOCUS_BY_PROFILE["destination"])
    if record and profile == "destination" and record.country in COUNTRY_STYLE_HINTS:
        return f"{COUNTRY_STYLE_HINTS[record.country].lower()} character and local scenery"
    return focus


def destination_copy(value: object) -> DestinationCopy:
    record = _record_for(value)
    name = _display_name(value, record)
    if not name:
        return DestinationCopy(
            arc="Time to explore at your own pace",
            leisure_options=LEISURE_BY_PROFILE["destination"],
            arrival_focus="local scenery and destination character",
        )
    profile = _profile(record)
    return DestinationCopy(
        arc=_arc_for_record(name, record),
        leisure_options=LEISURE_OVERRIDES.get(name, LEISURE_BY_PROFILE.get(profile, LEISURE_BY_PROFILE["destination"])),
        arrival_focus=_arrival_focus_for_record(record),
    )


def destination_arc_fallback(value: object) -> str:
    """Return premium Journey Arc fallback copy for any registered destination."""

    return destination_copy(value).arc


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

    record = _record_for(value)
    name = _display_name(value, record)
    if not name:
        return "Open time today is left flexible, with room to relax, explore independently, or settle into the day."

    context = _rows_text(rows)
    options = _choose_leisure_options(destination_copy(name).leisure_options, context)
    return destination_leisure_sentence(name, rows, options)


def _mode_label(mode: object) -> str:
    value = str(mode or "").strip().lower()
    if value == "coach":
        return "coach"
    if value == "bus":
        return "coach"
    if value == "train":
        return "rail"
    if value == "flight":
        return "flight"
    if value in {"ferry", "cruise"}:
        return value
    return value


def _clean_place(value: object) -> str:
    text = polish_title(str(value or "").strip())
    text = re.sub(r"\s+", " ", text).strip()
    return text


def travel_day_intro(origin: object, destination: object, mode: object = "") -> str:
    """Return a premium generic travel-day intro for registered destinations."""

    origin_text = _clean_place(origin)
    destination_record = _record_for(destination)
    destination_text = _display_name(destination, destination_record)
    if not destination_text:
        return "Today is arranged as a clear travel day, with the route and arrival details grouped below."

    focus = destination_copy(destination_text).arrival_focus
    mode_text = _mode_label(mode)
    if origin_text and origin_text.lower() == destination_text.lower():
        origin_text = ""

    destination_focus = f"{destination_text}’s {focus}"
    if origin_text and mode_text:
        return f"Travel from {origin_text} to {destination_text} by {mode_text}, with the day shaped around the move into {destination_focus}."
    if origin_text:
        return f"Travel from {origin_text} to {destination_text}, with the day shaped around the move into {destination_focus}."
    if mode_text:
        return f"Travel to {destination_text} by {mode_text}, with the day shaped around {destination_focus}."
    return f"Travel to {destination_text}, with the day shaped around {destination_focus}."

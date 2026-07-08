"""Classify destination/chapter experience phrases for journey arcs."""

from __future__ import annotations

import re
from dataclasses import dataclass

from itinerary_generation.client_text_decisions import destination_logistics_phrase, is_destination_logistics_only
from itinerary_generation.common import get_primary_city, get_row_type
from itinerary_generation.destination_copy import destination_arc_fallback
from itinerary_generation.nutshell_domain import has_nutshell_journey
from itinerary_generation.summaries_text import _compact_arc_phrase, _has
from itinerary_generation.transport import has_glass_igloo_or_arctic_resort


@dataclass(frozen=True)
class ExperienceSignals:
    text: str
    row_types: set[str]
    primary_experience_rows: list[dict]
    chapter_city: str
    has_arrival: bool
    has_departure: bool
    has_hotel_only: bool
    travel_only_with_hotel: bool
    has_nutshell: bool
    has_self_drive: bool
    has_lagoon: bool
    has_silfra: bool
    has_golden: bool
    has_south: bool
    has_adventure: bool
    has_whale: bool
    has_fjord: bool
    has_food: bool
    has_tallinn: bool
    has_city: bool
    has_nature: bool
    has_aurora: bool
    has_leisure: bool
    has_reindeer_sami: bool
    has_cable: bool
    has_flight: bool


_EFFECTIVE_KIND_KEY = "effective_" + "type"
_ROW_KIND_KEY = "type"


def _experience_kind(row: dict) -> str:
    return str(row.get(_EFFECTIVE_KIND_KEY) or row.get(_ROW_KIND_KEY) or "")


def _is_primary_experience_row(row: dict) -> bool:
    return get_row_type(row) == "Activity" and _experience_kind(row) == "Activity"


def _primary_experience_rows(rows):
    return [row for row in rows if _is_primary_experience_row(row)]


def _signature_route_rows(rows):
    result = []
    for row in rows:
        source_text = " ".join(str(row.get(key, "")) for key in ("title", "original_title", "details")).lower()
        if has_nutshell_journey([row]) or _has(
            source_text,
            "norway in a nutshell",
            "flåm",
            "flam railway",
            "nærøyfjord",
            "naeroyfjord",
        ):
            result.append(row)
    return result


def _text_rows(rows, primary_experience_rows):
    text_rows = []
    seen_text_row_ids = set()
    for candidate_row in [*primary_experience_rows, *_signature_route_rows(rows)]:
        identity = id(candidate_row)
        if identity in seen_text_row_ids:
            continue
        seen_text_row_ids.add(identity)
        text_rows.append(candidate_row)
    return text_rows or rows


def _experience_text(rows):
    return " ".join(
        " ".join([
            str(row.get("city", "")),
            str(row.get("title", "")),
            str(row.get("original_title", "")),
            str(row.get("details", "")),
            " ".join(row.get("includes", []) or []),
        ]).lower()
        for row in rows
    )


def _build_signals(rows):
    primary_rows = _primary_experience_rows(rows)
    text = _experience_text(_text_rows(rows, primary_rows))
    row_types = {get_row_type(row) for row in rows}
    food_is_excluded = bool(re.search(
        r"\bfood\s+(?:and\s+drinks?\s+)?(?:are\s+)?excluded\b|\bdrinks?\s+(?:are\s+)?excluded\b",
        text,
        flags=re.IGNORECASE,
    ))
    return ExperienceSignals(
        text=text,
        row_types=row_types,
        primary_experience_rows=primary_rows,
        chapter_city=get_primary_city(rows) or "",
        has_arrival=any(get_row_type(row) == "Arrival" for row in rows),
        has_departure=any(get_row_type(row) == "Departure" for row in rows),
        has_hotel_only=row_types == {"Hotel"},
        travel_only_with_hotel=(
            row_types.issubset({"Hotel", "Transfer", "Flight", "Train", "Transport", "Cruise", "Ferry"})
            and any(get_row_type(row) == "Hotel" for row in rows)
        ),
        has_nutshell=(not primary_rows and has_nutshell_journey(rows)) or _has(text, "norway in a nutshell"),
        has_self_drive=_has(text, "self-drive", "self drive", "rental vehicle", "rental suv", "rental car"),
        has_lagoon=_has(text, "blue lagoon", "sky lagoon", "wellness", "7-step", "ritual") or bool(re.search(r"\bspa\b", text)),
        has_silfra=_has(text, "silfra", "snork"),
        has_golden=_has(text, "golden circle", "kerið", "kerid"),
        has_south=_has(text, "south coast", "diamond beach", "black sand"),
        has_adventure=_has(text, "atv", "quad", "glacier", "hike", "hiking", "crampon"),
        has_whale=_has(text, "whale", "wildlife", "rib boat"),
        has_fjord=_has(text, "fjord", "trollfjord", "cruise", "catamaran", "silent electric ship")
        or ("boat" in text and not _has(text, "stockholm", "vasa", "old town")),
        has_food=bool(primary_rows)
        and not food_is_excluded
        and _has(text, "food tour", "tasting", "smørrebrød", "secret food", "fish soup", "culinary"),
        has_tallinn=_has(text, "tallinn"),
        has_city=_has(text, "vasa", "old town", "museum", "walking tour", "city walk", "must-see", "guided visit", "helsinki guide", "senate square", "senate squate"),
        has_nature=_has(text, "forest tower", "forgotten giants", "nature hike", "haukland", "henningsvær", "photo tour", "arctic landscape"),
        has_aurora=_has(text, "northern light", "aurora"),
        has_leisure=_has(text, "leisure", "spend time at leisure", "free time", "explore"),
        has_reindeer_sami=_has(text, "reindeer", "sámi", "sami", "husky", "santa claus village"),
        has_cable=_has(text, "fjellheisen", "cable car", "funicular", "fløibanen", "floibanen"),
        has_flight=_has(text, "flight"),
    )


def _logistics_only_phrase(rows, signals):
    if signals.primary_experience_rows or not is_destination_logistics_only(rows):
        return ""
    text = signals.text
    if _has(text, "northern light village", "panorama suite"):
        return "Northern Lights village stay"
    if signals.has_nutshell:
        return "Norway in a Nutshell and scenic rail"
    if _has(text, "spend time at leisure onboard the cruise") and signals.row_types == {"Cruise"}:
        return "Coastal cruise at leisure"
    if _has(text, "cruise to bergen") and _has(text, "kirkenes"):
        return "Cruise departure towards Bergen"
    if _has(text, "cruise arrival to bergen", "arrival to bergen"):
        return "Cruise arrival and Bergen stay"
    if signals.has_leisure and signals.chapter_city:
        return destination_arc_fallback(signals.chapter_city)
    return destination_logistics_phrase(rows, chapter=signals.chapter_city)


def _add_iceland_candidates(candidates, signals):
    text = signals.text
    if _has(text, "borgarfjörður", "borgarfjordur", "hraunfossar", "barnafoss"):
        candidates.append("Borgarfjörður valley and waterfalls")
    if _has(text, "snæfellsnes", "snaefellsnes", "kirkjufell", "arnarstapi"):
        candidates.append("Snæfellsnes Peninsula highlights")
    if _has(text, "katla") and _has(text, "seljalandsfoss", "skógafoss", "skogafoss", "reynisfjara"):
        candidates.append("South Coast waterfalls and Katla Ice Cave")
    elif _has(text, "south coast waterfalls", "seljalandsfoss", "skógafoss", "skogafoss", "reynisfjara"):
        candidates.append("South Coast waterfalls and glacier hike")
    if _has(text, "skaftafell", "vatnajökull", "vatnajokull") and _has(text, "jökulsárlón", "jokulsarlon", "diamond beach"):
        candidates.append("Vatnajökull glacier and Jökulsárlón")
    elif _has(text, "jökulsárlón", "jokulsarlon", "diamond beach", "ice cave"):
        candidates.append("Glacier lagoon and ice caves")
    if _has(text, "eastfjords", "egilsstaðir", "egilsstadir", "hallormsstaðaskógar", "lagafljót"):
        candidates.append("Eastfjords and local life")
    if _has(text, "dettifoss", "mývatn", "myvatn", "goðafoss", "godafoss", "north iceland"):
        candidates.append("North Iceland waterfalls and Mývatn")
    if signals.has_whale and _has(text, "hauganes", "return to reykjavík", "return to reykjavik"):
        candidates.append("Whale watching and return to Reykjavík")


def _add_route_and_city_candidates(candidates, signals):
    text = signals.text
    if _has(text, "oslofjord", "oslo fjord"):
        candidates.append("Oslofjord cruise and capital welcome" if signals.has_arrival else "City sights and Oslofjord cruising")
    if signals.chapter_city.lower() == "kristiansand" and _has(text, "coastal cruise", "cruise to bergen", "southern norway", "southern coastal"):
        candidates.append("South Coast and coastal cruise")
    if _has(text, "otra river", "kayaking", "kayak"):
        candidates.append("Otra River kayaking and southern coast")
    if _has(text, "lysefjord", "preikestolen", "pulpit rock"):
        candidates.append("Lysefjord and Preikestolen cruise")
    if _has(text, "guided walking tour of bergen", "bergen past & present") and signals.has_cable:
        candidates.append("Historic Bergen and Fløibanen views")
    if signals.has_nutshell and signals.has_food:
        candidates.append("Norway in a Nutshell and Oslo food tour")
    if _has(text, "spend time at leisure onboard the cruise") and signals.row_types == {"Cruise"}:
        candidates.append("Coastal cruise at leisure")
    if _has(text, "cruise to bergen") and _has(text, "kirkenes"):
        candidates.append("Cruise departure towards Bergen")
    if _has(text, "cruise arrival to bergen", "arrival to bergen"):
        candidates.append("Cruise arrival and Bergen stay")
    if signals.has_tallinn:
        candidates.append("Tallinn Old Town day trip")
    if signals.has_nutshell:
        candidates.append("Norway in a Nutshell and scenic rail")
    elif _has(text, "nærøyfjord", "naeroyfjord") and _has(text, "stegastein", "borgund"):
        candidates.append("Nærøyfjord, Stave Church and Stegastein")
    elif _has(text, "foot", "walking tour") and _has(text, "boat", "city cruise") and signals.chapter_city.lower() == "bergen":
        candidates.append("Scenic rail and Bergen by foot and boat")
    elif _has(text, "nærøyfjord", "naeroyfjord", "flåmsbanen", "flamsbanen", "flåm railway", "flam railway"):
        candidates.append("Scenic rail and fjord travel")
    elif _has(text, "scenic train", "train transfer", "rail") and signals.chapter_city:
        candidates.append(f"Scenic rail to {signals.chapter_city}")
    if signals.has_golden and signals.has_silfra:
        candidates.append("Golden Circle and Silfra snorkelling")
    elif signals.has_silfra:
        candidates.append("Silfra snorkelling")
    elif signals.has_golden:
        candidates.append("Golden Circle route")


def _add_theme_candidates(candidates, signals):
    text = signals.text
    if signals.has_lagoon and signals.has_self_drive and signals.has_whale:
        candidates.append("Lagoon, self-drive route and whale watching")
    elif signals.has_lagoon and signals.has_self_drive:
        candidates.append("Lagoon and scenic self-drive route")
    elif signals.has_lagoon:
        candidates.append("Blue Lagoon experience" if "blue lagoon" in text else "Sky Lagoon experience" if "sky lagoon" in text else "Lagoon and wellness")
    if signals.has_south and signals.has_adventure:
        candidates.append("South Coast scenery and soft adventure")
    elif signals.has_south:
        candidates.append("South Coast scenery")
    if signals.has_reindeer_sami and signals.has_aurora:
        if "santa claus village" in text:
            candidates.append("Northern Lights, Santa Village and Arctic experiences")
        elif signals.has_fjord or signals.has_nature:
            candidates.append("Sámi culture, fjords and northern lights")
        else:
            candidates.append("Northern Lights, Sámi culture and Arctic experiences")
    elif signals.has_reindeer_sami:
        candidates.append("Sámi culture and Arctic experiences")
    elif signals.has_aurora and signals.has_whale:
        candidates.append("Wildlife, Northern Lights and Arctic coast")
    elif signals.has_aurora:
        candidates.append("Northern Lights experiences")


def _add_fjord_and_experience_candidates(candidates, signals):
    text = signals.text
    chapter_city = signals.chapter_city
    if _has(text, "trollfjord"):
        candidates.append("Lofoten scenery and Trollfjord cruising")
    elif _has(text, "lofoten", "henningsvær", "haukland", "reine", "vestvågøy", "flakstadøy"):
        candidates.append("Lofoten scenery and photography")
    elif signals.has_fjord and signals.has_city and chapter_city.lower() == "oslo":
        candidates.append("City sights and Oslofjord cruising")
    elif signals.has_fjord and signals.has_cable:
        if _has(text, "bergen", "fløibanen", "floibanen") and not _has(text, "tromsø", "tromso", "alta", "svalbard", "kiruna"):
            candidates.append("City, fjord and funicular")
        elif _has(text, "arctic", "tromsø", "tromso", "alta", "svalbard", "kiruna"):
            candidates.append("Arctic fjords and viewpoints")
        else:
            candidates.append("Fjord views and funicular")
    elif signals.has_fjord and signals.has_whale:
        candidates.append("Coastal wildlife and fjord scenery")
    elif signals.has_fjord:
        if _has(text, "bergen") and not _has(text, "arctic", "tromsø", "tromso", "alta", "svalbard", "kiruna"):
            candidates.append("Bergen fjords and coastal cruising")
        else:
            candidates.append("Fjord scenery and coastal cruising")

    if signals.has_city and _has(text, "vasa", "old town", "stockholm"):
        candidates.append("Old Town, Vasa Museum and city discovery")
    elif signals.has_city and signals.has_arrival:
        candidates.append("Arrival and guided city discovery")
    elif signals.has_city:
        candidates.append("Guided city discovery")
    if signals.has_food and not any("food" in c.lower() for c in candidates):
        candidates.append("Local food culture")
    if signals.has_nature and not any(marker in " ".join(candidates).lower() for marker in ["nature", "lofoten", "arctic fjords", "south coast"]):
        candidates.append("Scenic nature experiences")
    if signals.has_leisure and len(candidates) < 2:
        candidates.append(destination_arc_fallback(chapter_city))


def _add_fallback_candidates(candidates, signals):
    text = signals.text
    chapter_city = signals.chapter_city
    if not candidates and _has(text, "coach transfer", "bus 150", "long distance panorama coach") and signals.has_aurora:
        candidates.append("Coach journey and Northern Lights")
    if signals.has_departure and not candidates:
        candidates.append(f"Departure from {chapter_city}" if chapter_city else "Departure arrangements")
    if signals.has_arrival and not candidates:
        candidates.append(f"Welcome to {chapter_city}" if chapter_city else "Arrival and time to settle in")
    if signals.has_hotel_only:
        candidates.append(f"Welcome to {chapter_city}" if chapter_city else "Accommodation as listed")
    if signals.travel_only_with_hotel and not candidates:
        if signals.has_departure:
            candidates.append(f"Departure from {chapter_city}" if chapter_city else "Departure arrangements")
        elif chapter_city:
            candidates.append(f"Welcome to {chapter_city}")
        elif signals.row_types.intersection({"Train", "Transport", "Cruise", "Ferry"}):
            candidates.append("Scenic route day")
        else:
            candidates.append("Arrival and time to settle in")
    if not candidates:
        if signals.has_flight and chapter_city:
            candidates.append(f"Welcome to {chapter_city}")
        elif signals.row_types.intersection({"Train", "Transport", "Cruise", "Ferry"}):
            candidates.append("Scenic route day")
        else:
            candidates.append(destination_arc_fallback(chapter_city))


def _candidate_phrases(signals):
    candidates = []
    _add_iceland_candidates(candidates, signals)
    _add_route_and_city_candidates(candidates, signals)
    _add_theme_candidates(candidates, signals)
    _add_fjord_and_experience_candidates(candidates, signals)
    _add_fallback_candidates(candidates, signals)
    return candidates


def _compact_experience_phrase(candidates, chapter_city):
    primary = candidates[0]
    if len(candidates) > 1:
        combined = f"{primary}, {candidates[1].lower()}"
        if len(combined) <= 48 and not any(word in primary.lower() for word in candidates[1].lower().split()[:2]):
            return _compact_arc_phrase([combined, primary], chapter=chapter_city)
    return _compact_arc_phrase([primary], chapter=chapter_city)


def describe_city_experience(rows):
    signals = _build_signals(rows)
    if has_glass_igloo_or_arctic_resort(rows):
        return "Arctic resort and glass igloo stay"
    logistics_phrase = _logistics_only_phrase(rows, signals)
    if logistics_phrase:
        return logistics_phrase
    return _compact_experience_phrase(_candidate_phrases(signals), signals.chapter_city)

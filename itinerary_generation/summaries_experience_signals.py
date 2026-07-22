"""Source-backed experience signal extraction."""
from __future__ import annotations

import re
from dataclasses import dataclass

from itinerary_generation.common import get_primary_city, get_row_type
from itinerary_generation.nutshell_domain import has_nutshell_journey
from itinerary_generation.nutshell_signature import canonical_nutshell_title
from itinerary_generation.summaries_text import _has

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
    nutshell_title: str
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
        nutshell_title=canonical_nutshell_title(rows),
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


"""Norway-specific activity product matching."""

from __future__ import annotations

import re
from typing import Any

from place_aliases import canonicalize_place_name
from text_polish import polish_title

from itinerary_generation.activity_product_core import ActivityProductFingerprint, match_product
from itinerary_generation.activity_product_text import canonicalize_activity_route_source
from itinerary_generation.transport_norway import (
    _is_norway_in_a_nutshell_text,
    extract_norway_nutshell_route_legs,
    extract_norway_nutshell_route_points,
)


def _legs_from_route_points(points: list[str]) -> tuple[dict[str, str], ...]:
    if len(points) < 2:
        return ()
    return tuple({"origin": points[index], "destination": points[index + 1], "mode": ""} for index in range(len(points) - 1))


def _direct_route_points_from_source(source: str) -> list[str]:
    city = r"Bergen|Oslo|Flåm|Flam|Voss|Gudvangen|Myrdal"
    patterns = (
        rf"\b(?P<origin>{city})\s+to\s+(?P<destination>{city})\b",
        rf"\bnorway\s+in\s+a\s+nutshell\s+(?P<origin>{city})\s+to\s+(?P<destination>{city})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, source, flags=re.IGNORECASE)
        if not match:
            continue
        origin = canonicalize_place_name(polish_title(match.group("origin")))
        destination = canonicalize_place_name(polish_title(match.group("destination")))
        if origin and destination and origin.lower() != destination.lower():
            return [origin, destination]
    return []


def _should_preserve_nutshell_origin(source: str) -> bool:
    city = r"Bergen|Oslo|Flåm|Flam|Voss|Gudvangen|Myrdal"
    return bool(
        re.search(rf"^\s*(?:{city})\s+to\s+(?:{city})\s*\|\s*Norway\s+in\s+a\s+Nutshell", source, flags=re.IGNORECASE)
        or re.search(rf"\b(?:Nærøyfjord|Naeroyfjord)[^\n:|]{{0,160}}\b(?:{city})\s+to\s+(?:{city})\s*(?:[:|,\-]|$)", source, flags=re.IGNORECASE)
        or re.search(rf"\b(?:luggage\s+(?:transfer|porter|service)|porter\s+service)[^\n:|]{{0,160}}\b(?:{city})\s+to\s+(?:{city})\b", source, flags=re.IGNORECASE)
        or (
            re.search(rf"^\s*(?:{city})\s+to\s+(?:{city})\s*:", source, flags=re.IGNORECASE)
            and any(marker in source.lower() for marker in ("flåm train", "flam train", "nærøyfjord", "naeroyfjord", "luggage transfer", "fjord cruise"))
        )
        or re.search(rf"\b(?:Bergen|Oslo)\s+to\s+(?:Bergen|Oslo)\b", source, flags=re.IGNORECASE) and "nutshell" in source.lower()
    )


def _route_title_from_points(points: list[str], *, preserve_origin: bool = False) -> str:
    if len(points) >= 2 and preserve_origin:
        return f"Norway in a Nutshell from {polish_title(points[0])} to {polish_title(points[-1])}"
    if points:
        return f"Norway in a Nutshell to {polish_title(points[-1])}"
    return "Norway in a Nutshell"


def _is_bergen_guided_flam_day_tour(source_lower: str) -> bool:
    """True for Bergen-to-Flåm guided day tours sold separately from Nutshell."""

    has_bergen_origin = "bergen" in source_lower
    has_flam_product = "flåm" in source_lower or "flam" in source_lower
    has_guided_day_tour = any(marker in source_lower for marker in ("guided day tour", "guided discovery", "day tour to flåm", "day tour to flam"))
    has_route_components = any(marker in source_lower for marker in ("flåm railway", "flam railway", "nærøyfjord", "naeroyfjord", "fjord cruise"))
    has_roundtrip_legs = "voss to bergen" in source_lower or "coach, voss to bergen" in source_lower or "back to bergen" in source_lower
    return has_bergen_origin and has_flam_product and has_guided_day_tour and has_route_components and has_roundtrip_legs


def match_norway_activity(
    row: dict[str, Any] | None,
    source: str,
    source_lower: str,
    source_title: str,
) -> ActivityProductFingerprint | None:
    """Match Norway route/fjord/funicular products."""

    if _is_bergen_guided_flam_day_tour(source_lower):
        return match_product(
            "bergen_guided_flam_day_tour",
            "guided_scenic_day_tour",
            "Bergen Guided Day Tour to Flåm with Flåm Railway & Fjord Cruise",
            source_title=source_title,
            variant_tags=("flam_railway", "fjord_cruise", "coach", "guided"),
        )

    if _is_norway_in_a_nutshell_text(source_lower):
        if row:
            original_title = str(row.get("original_title", "") or "")
            title = str(row.get("title", "") or "")
            route_fields = [
                original_title or title,
                str(row.get("details", "") or ""),
                str(row.get("description", "") or ""),
                str(row.get("raw", "") or ""),
                str(row.get("route", "") or ""),
                str(row.get("subtitle", "") or ""),
            ]
            route_source = canonicalize_activity_route_source("\n".join(value for value in route_fields if value.strip()))
        else:
            route_source = canonicalize_activity_route_source(source)
        direct_points = _direct_route_points_from_source(route_source)
        points = extract_norway_nutshell_route_points(route_source) or direct_points
        legs = tuple(extract_norway_nutshell_route_legs(route_source)) or _legs_from_route_points(points)
        tags: list[str] = []
        if "luggage" in source_lower and ("porter" in source_lower or "service" in source_lower):
            tags.append("luggage_service")
        if "part 1" in source_lower:
            tags.append("part_1")
        if "part 2" in source_lower:
            tags.append("part_2")
        return match_product(
            "norway_in_a_nutshell",
            "scenic_route",
            _route_title_from_points(points, preserve_origin=_should_preserve_nutshell_origin(route_source)),
            source_title=source_title or "Norway in a Nutshell",
            variant_tags=tuple(tags),
            route_legs=legs,
        )

    if "fløibanen" in source_lower or "floibanen" in source_lower or "funicular" in source_lower or "funicual" in source_lower:
        return match_product("floibanen_funicular", "ticket", "Fløibanen Funicular", source_title=source_title)

    if "must-see bergen" in source_lower and ("foot" in source_lower or "boat" in source_lower or "ferry" in source_lower):
        return match_product("bergen_foot_and_boat", "walking_boat_tour", "Bergen Walking & Boat Tour", source_title=source_title, variant_tags=("walking", "boat"))

    if "stegastein" in source_lower and ("electric minibus" in source_lower or "electric bus" in source_lower or "viewpoint" in source_lower):
        return match_product(
            "flam_stegastein_electric_minibus",
            "sightseeing_activity",
            "Electric Minibus to Stegastein Viewpoint",
            source_title=source_title,
            variant_tags=("electric_bus", "viewpoint", "flam"),
        )

    if "bergen" in source_lower and ("past & present" in source_lower or "past and present" in source_lower or "walk through bergen" in source_lower):
        return match_product("bergen_past_present_walk", "walking_tour", "Guided Walking Tour of Bergen Past & Present", source_title=source_title)

    if "bergen" in source_lower and "city drive" in source_lower:
        return match_product("bergen_city_drive", "private_drive", source_title if source_title else "Private Bergen City Drive", source_title=source_title)

    if "mostraumen" in source_lower:
        return match_product("mostraumen_fjord_cruise", "fjord_cruise", "Mostraumen Fjord Cruise", source_title=source_title)

    if "geiranger" in source_lower and ("fjord cruise" in source_lower or "cruise day trip" in source_lower or "boat and bus" in source_lower):
        title = "Ålesund-Geiranger Fjord Tour by Boat and Bus" if "one way" in source_lower or "boat and bus" in source_lower else "Geiranger Fjord Cruise Day Trip"
        return match_product("geiranger_fjord_cruise", "fjord_cruise", title, source_title=source_title)

    if "ålesund" in source_lower and "hop" in source_lower and "off" in source_lower:
        return match_product("alesund_hop_on_hop_off", "ticket", "Ålesund Hop-On Hop-Off 24-Hour Ticket", source_title=source_title)

    return None

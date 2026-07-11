"""Norway-specific activity product matching."""

from __future__ import annotations

import re
from typing import Any

from itinerary_domain.activity_product_core import ActivityProductFingerprint, match_product
from itinerary_domain.activity_product_text import canonicalize_activity_route_source
from itinerary_domain.fjordtours_activity_catalogue import match_fjordtours_nutshell_addon
from itinerary_domain.transport_norway import _is_norway_in_a_nutshell_text
from itinerary_domain.nutshell_parsing import is_source_backed_nutshell_route_package
from itinerary_domain.nutshell_domain import build_nutshell_journey


def _is_bergen_guided_flam_day_tour(source_lower: str) -> bool:
    """True for Bergen-to-Flåm guided day tours sold separately from Nutshell."""

    has_bergen_origin = "bergen" in source_lower
    has_flam_product = "flåm" in source_lower or "flam" in source_lower
    has_guided_day_tour = any(marker in source_lower for marker in ("guided day tour", "guided discovery", "day tour to flåm", "day tour to flam"))
    has_route_components = any(marker in source_lower for marker in ("flåm railway", "flam railway", "nærøyfjord", "naeroyfjord", "fjord cruise"))
    has_roundtrip_legs = "voss to bergen" in source_lower or "coach, voss to bergen" in source_lower or "back to bergen" in source_lower
    return has_bergen_origin and has_flam_product and has_guided_day_tour and has_route_components and has_roundtrip_legs


def _is_explicit_bergen_city_drive(source_lower: str, source_title: str) -> bool:
    """True when the supplier title/product identity is a Bergen city drive.

    City-drive rows can mention Mt Fløyen or Fløibanen in highlights, but those
    incidental landmark references must not outrank the explicit product title.
    """

    title_lower = source_title.lower()
    return (
        "bergen" in source_lower
        and "city drive" in source_lower
        and (
            "city drive" in title_lower
            or re.search(r"\bbergen\s*:\s*(?:private\s+)?city\s+drive\b", source_lower)
            or re.search(r"\b(?:private\s+)?bergen\s+city\s+drive\b", source_lower)
        )
    )


def _is_explicit_floibanen_product(source_lower: str, source_title: str) -> bool:
    """True for dedicated Fløibanen/funicular products, not incidental highlights."""

    title_lower = source_title.lower()
    broad_bergen_tour_title = bool(
        re.search(r"\b(?:best\s+of\s+bergen|bergen.*walking\s+tour|walking\s+tour.*bergen|private\s+walking\s+tour)\b", title_lower)
    )
    explicit_title = any(
        marker in title_lower
        for marker in ("fløibanen", "floibanen", "funicular", "funicual")
    ) and not broad_bergen_tour_title
    explicit_ticket_line = bool(
        re.search(
            r"\bbergen\s*(?::|round[-\s]?trip|round\s+trip)[^.\n|]{0,80}\b(?:fløibanen|floibanen|funicular|funicual)\b",
            source_lower,
        )
    )
    ticket_only = bool(re.search(r"\b(?:ticket|tickets|admission)\b", title_lower))
    return explicit_title or (explicit_ticket_line and ticket_only)


def _is_standalone_naeroyfjord_cruise(source_lower: str) -> bool:
    """True for a Nærøyfjord cruise sold as an activity, not a route package."""

    has_naeroyfjord = "nærøyfjord" in source_lower or "naeroyfjord" in source_lower
    has_cruise_experience = "cruise" in source_lower and any(
        marker in source_lower
        for marker in ("sightseeing", "fjord cruise", "day trip", "round-trip", "round trip", "duration", "meeting point")
    )
    has_route_package_marker = any(
        marker in source_lower
        for marker in (
            "norway in a nutshell",
            "flåm railway",
            "flam railway",
            "flåm train",
            "flam train",
            "bergen railway",
            "luggage transfer",
            "coach bergen to",
            "panorama coach",
            "gudvangen to flåm",
            "gudvangen to flam",
            "flåm to myrdal",
            "flam to myrdal",
        )
    )
    return has_naeroyfjord and has_cruise_experience and not has_route_package_marker


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

    if _is_standalone_naeroyfjord_cruise(source_lower):
        return match_product("naeroyfjord_sightseeing_cruise", "fjord_cruise", "Nærøyfjord Sightseeing Cruise", source_title=source_title)

    if _is_norway_in_a_nutshell_text(source_lower) or is_source_backed_nutshell_route_package(source):
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
        journey = build_nutshell_journey(
            row,
            source=route_source,
            source_title=source_title,
        )
        if journey is None:
            return None
        tags: list[str] = []
        if "luggage" in source_lower and ("porter" in source_lower or "service" in source_lower):
            tags.append("luggage_service")
        if "part 1" in source_lower:
            tags.append("part_1")
        if "part 2" in source_lower:
            tags.append("part_2")
        return match_product(
            journey.canonical_family,
            journey.product_type,
            journey.client_title,
            source_title=source_title or journey.source_title or journey.product_name,
            variant_tags=tuple(tags),
            route_legs=journey.legacy_route_legs,
            warnings=journey.warnings,
        )

    if _is_explicit_bergen_city_drive(source_lower, source_title):
        return match_product(
            "bergen_city_drive",
            "private_drive",
            source_title if source_title else "Private Bergen City Drive",
            source_title=source_title,
        )

    if _is_explicit_floibanen_product(source_lower, source_title):
        return match_product("floibanen_funicular", "ticket", "Fløibanen Funicular", source_title=source_title)

    if "borgund" in source_lower and "stegastein" in source_lower:
        return match_product(
            "flam_borgund_stegastein_tour",
            "sightseeing_activity",
            "Borgund Stave Church & Stegastein Viewpoint Tour",
            source_title=source_title,
            variant_tags=("stave_church", "viewpoint", "flam"),
        )

    fjordtours_entry = match_fjordtours_nutshell_addon(source, source_title)
    if fjordtours_entry:
        return match_product(
            fjordtours_entry.rule_id,
            fjordtours_entry.product_type,
            fjordtours_entry.display_title,
            source_title=source_title,
            variant_tags=fjordtours_entry.variant_tags,
        )

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

    if "bergen" in source_lower and re.search(r"\b(best\s+of\s+bergen|half[-\s]?day\s+private\s+walking\s+tour|private\s+walking\s+tour)\b", source_lower):
        return match_product("bergen_best_private_walk", "walking_tour", "Best of Bergen Private Walking Tour", source_title=source_title)

    if "bergen" in source_lower and ("past & present" in source_lower or "past and present" in source_lower or "walk through bergen" in source_lower):
        return match_product("bergen_past_present_walk", "walking_tour", "Guided Walking Tour of Bergen Past & Present", source_title=source_title)

    if "mostraumen" in source_lower:
        return match_product("mostraumen_fjord_cruise", "fjord_cruise", "Mostraumen Fjord Cruise", source_title=source_title)

    if "geiranger" in source_lower and ("fjord cruise" in source_lower or "cruise day trip" in source_lower or "boat and bus" in source_lower):
        title = "Ålesund-Geiranger Fjord Tour by Boat and Bus" if "one way" in source_lower or "boat and bus" in source_lower else "Geiranger Fjord Cruise Day Trip"
        return match_product("geiranger_fjord_cruise", "fjord_cruise", title, source_title=source_title)

    if "ålesund" in source_lower and "hop" in source_lower and "off" in source_lower:
        return match_product("alesund_hop_on_hop_off", "ticket", "Ålesund Hop-On Hop-Off 24-Hour Ticket", source_title=source_title)

    return None

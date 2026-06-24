"""Premium deterministic route copy for Nordic travel days.

This module keeps route wording separate from parser facts.  It only uses
resolved origin/destination/mode data to choose better client-facing copy; it
must not invent new timings, hotels or inclusions.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Mapping, Sequence

from itinerary_generation.common import TRANSPORT_TYPES, get_row_type
from itinerary_generation.destination_registry import destination_for_alias
from itinerary_generation.nutshell_domain import resolve_nutshell_journey
from itinerary_generation.transport_detection import is_route_transfer
from itinerary_generation.transport_domain.routes import get_route_points_for_transport
from itinerary_generation.transport_domain.titles import get_transfer_travel_title
from itinerary_generation.transport_model import get_transport_source_text
from itinerary_generation.transport_safety import base_destination_from_terminal, normalize_transport_place
from text_polish import polish_title


@dataclass(frozen=True)
class RouteCopyProfile:
    origin: str
    destination: str
    mode: str
    title: str
    intro: str
    description: str
    style: str
    highlights: tuple[str, ...] = ()


_MODE_ALIASES = {
    "bus": "coach",
    "coach transfer": "coach",
    "bus transfer": "coach",
    "train transfer": "train",
    "scenic train transfer": "train",
    "rail": "train",
    "railway": "train",
    "ferry transfer": "ferry",
    "cruise transfer": "cruise",
    "coastal cruise": "coastal_cruise",
    "coastal_cruise": "coastal_cruise",
    "atlantic coastal cruise": "coastal_cruise",
    "norway in a nutshell": "norway_in_a_nutshell",
    "self drive": "self_drive",
    "self-drive": "self_drive",
    "drive": "self_drive",
}


_MODE_LABELS = {
    "train": "Rail segment",
    "coach": "Coach connection",
    "bus": "Coach connection",
    "cruise": "Cruise segment",
    "ferry": "Ferry crossing",
    "fjord_cruise": "Fjord cruise",
    "flight": "Flight segment",
    "transfer": "Transfer",
    "self_drive": "Scenic drive",
}


_COMMON_ROUTES: dict[tuple[str, str, str], RouteCopyProfile] = {
    ("oslo", "kristiansand", "coach"): RouteCopyProfile(
        origin="Oslo",
        destination="Kristiansand",
        mode="coach",
        title="Oslo → Kristiansand",
        intro=(
            "Travel south from Oslo to Kristiansand, leaving the capital behind for Southern Norway’s coastal atmosphere. "
            "The coach journey is kept as the main connection of the day, with arrival arrangements handled clearly around it."
        ),
        description="A southbound coach connection from the capital towards Norway’s southern coast.",
        style="Scenic coach connection",
        highlights=("Southern Norway", "Coastal arrival", "Comfortable coach route"),
    ),
    ("kristiansand", "stavanger", "train"): RouteCopyProfile(
        origin="Kristiansand",
        destination="Stavanger",
        mode="train",
        title="Kristiansand → Stavanger",
        intro=(
            "Travel from Kristiansand to Stavanger by train, continuing west along Southern Norway towards the fjord gateway of Stavanger. "
            "The rail journey gives the day a clear structure before check-in on arrival."
        ),
        description="A westbound rail journey linking Southern Norway with Stavanger’s harbour and fjord country.",
        style="Scenic rail connection",
        highlights=("Southern Norway rail", "Stavanger arrival", "Fjord gateway"),
    ),
    ("stavanger", "bergen", "coastal_cruise"): RouteCopyProfile(
        origin="Stavanger",
        destination="Bergen",
        mode="coastal_cruise",
        title="Stavanger → Bergen",
        intro=(
            "Travel from Stavanger to Bergen by coastal cruise, with private transfers arranged around the port departure and hotel arrival. "
            "The day is presented as one coordinated door-to-door journey rather than separate logistics."
        ),
        description="A coordinated coastal transfer day, combining private port transfers with the scenic cruise leg to Bergen.",
        style="Coastal cruise transfer",
        highlights=("Coastal sailing", "Port-to-hotel coordination", "Bergen arrival"),
    ),
    ("bergen", "oslo", "norway_in_a_nutshell"): RouteCopyProfile(
        origin="Bergen",
        destination="Oslo",
        mode="norway_in_a_nutshell",
        title="Norway in a Nutshell to Oslo",
        intro=(
            "Follow the Norway in a Nutshell route from Bergen to Oslo, with rail, coach and fjord-cruise segments forming one carefully sequenced scenic journey. "
            "The day is structured around the route itself, not as a generic transfer."
        ),
        description=(
            "A signature Norway rail-and-fjord journey, combining mountain railway scenery, fjord villages and coordinated connections "
            "between Bergen and Oslo."
        ),
        style="Self-guided scenic journey — rail and fjord",
        highlights=("Bergen Railway", "Nærøyfjord cruise", "Flåm Railway"),
    ),
    ("oslo", "bergen", "norway_in_a_nutshell"): RouteCopyProfile(
        origin="Oslo",
        destination="Bergen",
        mode="norway_in_a_nutshell",
        title="Norway in a Nutshell to Bergen",
        intro=(
            "Follow the Norway in a Nutshell route from Oslo to Bergen, with mountain rail, fjord cruise and coach connections arranged as one scenic travel day."
        ),
        description=(
            "A classic rail-and-fjord journey from the capital towards Bergen, with the route presented as the day’s main experience."
        ),
        style="Self-guided scenic journey — rail and fjord",
        highlights=("Bergen Railway", "Nærøyfjord cruise", "Flåm Railway"),
    ),
    ("oslo", "bergen", "train"): RouteCopyProfile(
        origin="Oslo",
        destination="Bergen",
        mode="train",
        title="Oslo → Bergen",
        intro="Cross from Oslo to Bergen by rail, following one of Norway’s great mountain railway routes before arriving on the west coast.",
        description="A scenic rail connection across Norway’s mountain plateau towards the fjords.",
        style="Scenic rail journey",
        highlights=("Mountain railway", "West coast arrival", "Norwegian scenery"),
    ),
    ("stockholm", "copenhagen", "train"): RouteCopyProfile(
        origin="Stockholm",
        destination="Copenhagen",
        mode="train",
        title="Stockholm → Copenhagen",
        intro="Travel by rail from Stockholm to Copenhagen, linking Sweden’s capital with Denmark’s harbour city in a clear cross-border journey.",
        description="A cross-border rail journey between two Nordic capitals.",
        style="Nordic capital rail connection",
        highlights=("Cross-border rail", "Nordic capitals", "Copenhagen arrival"),
    ),
    ("helsinki", "rovaniemi", "train"): RouteCopyProfile(
        origin="Helsinki",
        destination="Rovaniemi",
        mode="train",
        title="Helsinki → Rovaniemi",
        intro="Travel north from Helsinki to Rovaniemi, with the rail journey marking the transition from the capital to Finnish Lapland.",
        description="A northbound Finnish rail journey from the capital towards Lapland.",
        style="Lapland rail connection",
        highlights=("Finnish rail", "Lapland arrival", "Arctic Circle gateway"),
    ),
    ("helsinki", "rovaniemi", "overnight_train"): RouteCopyProfile(
        origin="Helsinki",
        destination="Rovaniemi",
        mode="overnight_train",
        title="Helsinki → Rovaniemi",
        intro="Board the overnight train from Helsinki to Rovaniemi, turning the journey north into a comfortable transition towards Finnish Lapland.",
        description="An overnight rail journey from Helsinki to the Arctic Circle gateway.",
        style="Overnight Lapland rail journey",
        highlights=("Overnight train", "Lapland arrival", "Arctic Circle gateway"),
    ),
    ("reykjavik", "vik", "self_drive"): RouteCopyProfile(
        origin="Reykjavík",
        destination="Vík",
        mode="self_drive",
        title="Reykjavík → Vík",
        intro="Begin the South Coast drive from Reykjavík towards Vík, with waterfalls, black-sand coastline and open Icelandic landscapes shaping the route.",
        description="A South Coast self-drive day from Reykjavík towards Vík.",
        style="South Coast self-drive",
        highlights=("South Coast", "Waterfalls", "Black-sand coastline"),
    ),
}


def _key(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    record = destination_for_alias(text)
    canonical = record.name if record else polish_title(normalize_transport_place(base_destination_from_terminal(text) or text))
    return canonical.lower().replace("ø", "o").replace("ö", "o").replace("å", "a").replace("ä", "a").replace("æ", "ae").replace("é", "e").replace("í", "i")


def _display_place(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    record = destination_for_alias(text)
    return record.name if record else polish_title(normalize_transport_place(base_destination_from_terminal(text) or text))


def normalize_route_mode(mode: object, source_text: str = "") -> str:
    text = f"{mode or ''} {source_text or ''}".lower()
    if "norway in a nutshell" in text:
        return "norway_in_a_nutshell"
    if ("coastal" in text and "cruise" in text) or "atlantic coastal" in text:
        return "coastal_cruise"
    for marker, canonical in _MODE_ALIASES.items():
        if marker in text:
            return canonical
    if "overnight" in text and "train" in text:
        return "overnight_train"
    if "fjord cruise" in text or "nærøyfjord" in text or "naeroyfjord" in text:
        return "fjord_cruise"
    if "train" in text or "rail" in text:
        return "train"
    if "coach" in text or "bus" in text:
        return "coach"
    if "ferry" in text:
        return "ferry"
    if "cruise" in text:
        return "cruise"
    if "flight" in text:
        return "flight"
    if "drive" in text:
        return "self_drive"
    return str(mode or "").strip().lower()


def premium_mode_label(mode: object, source_text: str = "") -> str:
    canonical = normalize_route_mode(mode, source_text)
    return _MODE_LABELS.get(canonical, polish_title(str(mode or "").strip()) or "Journey leg")


def route_profile_for_places(origin: object, destination: object, mode: object = "", source_text: str = "") -> RouteCopyProfile | None:
    origin_key = _key(origin)
    destination_key = _key(destination)
    mode_key = normalize_route_mode(mode, source_text)
    if not origin_key or not destination_key or origin_key == destination_key:
        return None
    for candidate_mode in (mode_key, "train" if mode_key == "overnight_train" else "", "cruise" if mode_key == "coastal_cruise" else ""):
        if not candidate_mode:
            continue
        profile = _COMMON_ROUTES.get((origin_key, destination_key, candidate_mode))
        if profile:
            return profile
    return None


def route_profile_for_row(row: Mapping[str, object]) -> RouteCopyProfile | None:
    source_text = get_transport_source_text(row)
    journey = resolve_nutshell_journey(row)
    if journey is not None:
        origin = journey.origin or (journey.route_points[0] if journey.route_points else row.get("city", ""))
        destination = journey.destination or (journey.route_points[-1] if journey.route_points else "")
        return route_profile_for_places(origin, destination, "norway_in_a_nutshell", source_text)
    origin, destination = get_route_points_for_transport(row)
    if not origin:
        origin = row.get("city", "")
    return route_profile_for_places(origin, destination, get_row_type(row), source_text)


def _main_route_row(day_rows: Sequence[Mapping[str, object]]) -> Mapping[str, object] | None:
    travel_rows = [row for row in day_rows if get_row_type(row) in TRANSPORT_TYPES or get_row_type(row) == "Transfer" or is_route_transfer(row)]
    if not travel_rows:
        return None
    # Prefer named/scenic product rows over local transfers.
    for row in travel_rows:
        source = get_transport_source_text(row).lower()
        if "norway in a nutshell" in source or "nærøyfjord" in source or "naeroyfjord" in source:
            return row
    for row in travel_rows:
        source = get_transport_source_text(row).lower()
        if "coastal" in source and "cruise" in source:
            return row
    for row in travel_rows:
        if get_row_type(row) in TRANSPORT_TYPES:
            return row
    return travel_rows[0]


def route_intro_for_day(day_rows: Sequence[Mapping[str, object]], detail_level: str = "") -> str:
    row = _main_route_row(day_rows)
    if row is None:
        return ""
    profile = route_profile_for_row(row)
    if profile:
        return profile.intro

    origin, destination = get_route_points_for_transport(row) if get_row_type(row) in TRANSPORT_TYPES else ("", "")
    if not destination and is_route_transfer(row):
        # Route transfer rows often keep the endpoint inside the generated transfer title.
        from parser_modules.common import extract_route_points

        origin, destination = extract_route_points(get_transfer_travel_title(row))
    origin = _display_place(origin or row.get("city", ""))
    destination = _display_place(destination)
    mode = normalize_route_mode(get_row_type(row), get_transport_source_text(row))
    mode_label = {
        "train": "by rail",
        "coach": "by coach",
        "ferry": "by ferry",
        "cruise": "by cruise",
        "flight": "by flight",
        "self_drive": "by self-drive route",
    }.get(mode, "with the planned travel arrangements")
    if origin and destination and origin.lower() != destination.lower():
        return f"Travel from {origin} to {destination} {mode_label}, with arrival arrangements and the main journey details grouped below."
    if destination:
        return f"Continue to {destination} {mode_label}, with arrival arrangements and the main journey details grouped below."
    return ""

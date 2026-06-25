"""Route-led day-intro helpers."""

from __future__ import annotations

import re

from itinerary_generation.common import TRANSPORT_TYPES, get_row_type
from itinerary_generation.day_route_text import _canonical_route_city, create_travel_route_label
from itinerary_generation.destination_copy import travel_day_intro
from itinerary_generation.route_intelligence import route_profile_for_places
from itinerary_generation.transport import get_route_points_for_transport
from itinerary_generation.transport_safety import base_destination_from_terminal
from text_polish import polish_title


def _route_summary_from_rows(day_rows: list[dict]) -> tuple[str, str, str]:
    """Return origin, destination and main mode for route-led day intros."""

    origin = ""
    destination = ""
    mode = ""
    for row in day_rows:
        row_type = get_row_type(row)
        if row_type not in TRANSPORT_TYPES:
            continue
        if not mode:
            row_text = f'{row.get("title", "")} {row.get("details", "")} {row.get("original_title", "")}'.lower()
            if row_type == "Train" or "train" in row_text:
                mode = "train"
            elif row_type == "Flight" or "flight" in row_text:
                mode = "flight"
            elif row_type == "Cruise" or "cruise" in row_text:
                mode = "cruise"
            elif row_type == "Ferry" or "ferry" in row_text:
                mode = "ferry"
            elif "coach" in row_text or "bus" in row_text:
                mode = "coach"
            else:
                mode = row_type.lower()
        route_origin, route_destination = get_route_points_for_transport(row)
        if route_origin and not origin:
            origin = _canonical_route_city(base_destination_from_terminal(route_origin) or route_origin)
        if route_destination:
            destination = _canonical_route_city(base_destination_from_terminal(route_destination) or route_destination)
    return origin, destination, mode


def _premium_route_intro(origin: str, destination: str, mode: str, detail_level: str = "") -> str:
    """Return premium destination-aware route copy when a deterministic route exists."""

    origin = _canonical_route_city(origin)
    destination = _canonical_route_city(destination)
    mode = str(mode or "").lower()
    if not destination:
        return ""
    if origin and origin.lower() == destination.lower():
        origin = ""
    if mode == "nutshell" and not origin:
        return ""

    profile_mode = "norway_in_a_nutshell" if mode == "nutshell" else "coastal_cruise" if mode == "coastal_cruise" else mode
    profile = route_profile_for_places(origin, destination, profile_mode)
    if profile:
        return profile.intro

    if destination.lower() == "kristiansand":
        if origin:
            return f"Travel south from {origin} to Kristiansand, with the coach journey connecting the route to Norway’s southern coast." if mode == "coach" else f"Travel south from {origin} to Kristiansand, with the day shaped around the move into Norway’s southern coast."
        return "Travel towards Kristiansand today, with the day shaped around Norway’s southern coastal charm."
    if destination.lower() == "stavanger":
        if origin:
            return f"Travel from {origin} to Stavanger by train, continuing from the southern coast towards Norway’s fjord country." if mode == "train" else f"Travel from {origin} to Stavanger, continuing towards Norway’s fjord country."
        return "Travel towards Stavanger today, continuing towards Norway’s fjord country."
    if destination.lower() == "bergen" and mode in {"cruise", "ferry"}:
        if origin:
            return "Travel from {origin} to Bergen by coastal cruise, with the day arranged as a coordinated port-to-hotel journey.".format(origin=origin)
        return "Travel to Bergen by coastal cruise, with the day arranged as a coordinated port-to-hotel journey."
    generic_intro = travel_day_intro(origin, destination, mode)
    if generic_intro:
        return generic_intro
    if origin:
        connector = f" by {mode}" if mode in {"train", "coach", "ferry", "cruise", "flight"} else ""
        return f"Travel from {origin} to {destination}{connector}, with the day’s route and arrival arrangements grouped clearly below."
    return f"Travel to {destination}, with the day’s route and arrival arrangements grouped clearly below."


def _title_route_points(title: str, city: str = "") -> tuple[str, str]:
    """Infer coarse route endpoints from a planned day title."""

    text = str(title or "").strip()
    if not text:
        return "", polish_title(city) if city else ""
    if re.search(r"^travel\s+to\s+", text, flags=re.IGNORECASE):
        destination = re.sub(r"^travel\s+to\s+", "", text, flags=re.IGNORECASE).strip(" -:|")
        return "", polish_title(destination)
    nutshell_to = re.search(r"^norway\s+in\s+a\s+nutshell\s+to\s+(.+)$", text, flags=re.IGNORECASE)
    if nutshell_to:
        return "", polish_title(nutshell_to.group(1).strip(" -:|"))

    match = re.search(r"\bfrom\s+(.+?)\s+to\s+(.+)$", text, flags=re.IGNORECASE)
    if not match:
        match = re.search(r"^(.+?)\s+(?:→|->|to)\s+(.+)$", text, flags=re.IGNORECASE)
    if match:
        origin = polish_title(match.group(1).strip(" -:|"))
        destination = polish_title(match.group(2).strip(" -:|"))
        if origin.lower() in {"travel", "journey"}:
            origin = ""
        return origin, destination

    match = re.search(r"\bto\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+)$", text, flags=re.IGNORECASE)
    if match:
        destination = polish_title(match.group(1).strip(" -:|"))
        return "", destination
    return "", polish_title(city) if city else ""


def _travel_mode_from_title(title: str) -> str:
    """Infer a coarse transport mode from a title."""

    lower = str(title or "").lower()
    if "norway in a nutshell" in lower:
        return "nutshell"
    if "coastal cruise" in lower or "cruise transfer" in lower:
        return "coastal_cruise"
    if "cruise" in lower:
        return "cruise"
    if "ferry" in lower:
        return "ferry"
    if "train" in lower or "rail" in lower:
        return "train"
    if "coach" in lower or "bus" in lower:
        return "coach"
    if "flight" in lower:
        return "flight"
    return ""


__all__ = [
    "_canonical_route_city",
    "_premium_route_intro",
    "_route_summary_from_rows",
    "_title_route_points",
    "_travel_mode_from_title",
    "create_travel_route_label",
]

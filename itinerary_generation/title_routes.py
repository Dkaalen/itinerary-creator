from __future__ import annotations

import re

from parser_modules.common import extract_route_points
from text_polish import polish_title
from itinerary_generation.transport_norway import (
    NUTSHELL_ROUTE_PLACES,
    explicit_norway_nutshell_title,
    extract_norway_nutshell_route_points,
    should_preserve_nutshell_origin_label,
)

def _route_label_from_activity_text(text: str) -> str:
    explicit_title = explicit_norway_nutshell_title(text)
    if explicit_title:
        return explicit_title

    # Do not promote the first included leg (for example Oslo to Myrdal or
    # Flåm to Gudvangen) to the product title.  First build the complete route
    # from known Nutshell timetable/leg patterns and use the final endpoint.
    points = extract_norway_nutshell_route_points(text)
    if len(points) >= 2:
        origin = points[0] if should_preserve_nutshell_origin_label(text, points[0], points[-1]) else ""
        destination = points[-1]
    else:
        route_match = re.search(rf"\b({NUTSHELL_ROUTE_PLACES})\s+to\s+({NUTSHELL_ROUTE_PLACES})\b", text, flags=re.IGNORECASE)
        if route_match:
            origin, destination = route_match.group(1), route_match.group(2)
        else:
            origin, destination = extract_route_points(text)
    origin = polish_title(origin) if origin else ""
    destination = polish_title(destination) if destination else ""
    if origin and destination and origin.lower() != destination.lower():
        return f"Norway in a Nutshell from {origin} to {destination}"
    if destination:
        return f"Norway in a Nutshell to {destination}"
    return "Norway in a Nutshell"


def _looks_like_norway_in_a_nutshell(text: str) -> bool:
    lower = str(text or "").lower()
    if re.search(r"norway\s+in\s+a\s+(?:nutshell|nuthsell)", lower):
        return True
    has_flam = any(marker in lower for marker in ["flåm", "flam", "flåmsbana", "flamsbana", "flåm train", "flam train", "flåm railway", "flam railway"])
    has_fjord = any(marker in lower for marker in ["nærøyfjord", "naeroyfjord", "fjord cruise", "gudvangen", "voss", "geilo"])
    route_place = r"(?:bergen|oslo|fl[åa]m|voss|gudvangen|myrdal|geilo)"
    has_route = bool(re.search(rf"\b{route_place}\b[^.\n]{{0,160}}\bto\b[^.\n]{{0,160}}\b{route_place}\b", lower))
    return has_flam and has_fjord and has_route



def _extract_supplier_day_heading(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""
    first_line = next((line.strip() for line in raw.splitlines() if line.strip()), "")
    match = re.match(r"^Day\s+\d+\s*[:\-–]\s*(.+)$", first_line, flags=re.IGNORECASE)
    if not match:
        return ""
    heading = re.split(r"\s{2,}|\s+Overview\b|\s+What's included\b|\s+What’s included\b|\s+What to expect\b", match.group(1), maxsplit=1, flags=re.IGNORECASE)[0]
    heading = re.split(
        r"\s+(?:Embark|After\s+a|After\s+breakfast|Start\s+your|Continuing|Continue\s+your|"
        r"The\s+highlight|Your\s+adventure\s+begins|On\s+the\s+final|Finally|After\s+\w+|We start|"
        r"You will|You are|Prepare to|The first|A \d|At \w+|Once you|Afterwards|On your way)\b",
        heading,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    heading = heading.strip(" -:|.,")
    heading = re.sub(r"\bToday\b\s*$", "", heading, flags=re.IGNORECASE).strip(" -:|.,")
    if re.search(r"J[öo]kuls[áa]rl[óo]n", heading, flags=re.IGNORECASE) and "ice" in heading.lower():
        heading = "Explore Jökulsárlón Glacier Lagoon & Ice Caves"
    return polish_title(heading)




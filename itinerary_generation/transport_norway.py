"""Norway in a Nutshell transport detection and labels."""

from __future__ import annotations

import re

from text_polish import polish_title
from place_aliases import canonicalize_place_name


def _is_norway_in_a_nutshell_text(text):
    lower = str(text or "").lower()
    if "norway in a nutshell" in lower:
        return True
    has_flam = any(marker in lower for marker in ["flåm", "flam", "flåmsbana", "flamsbana", "flåm train", "flam train", "flåm railway", "flam railway"])
    has_fjord = any(marker in lower for marker in ["nærøyfjord", "naeroyfjord", "fjord cruise", "gudvangen", "voss"])
    return has_flam and has_fjord


def _clean_nutshell_place(value: str) -> str:
    return canonicalize_place_name(polish_title(str(value or "").strip(" -:|.,")))


def _direct_nutshell_pipe_route(text: str) -> tuple[str, str]:
    """Return the main route from compact pipe-style Nutshell rows.

    Supplier rows often arrive as ``Norway in a Nutshell | Oslo to Bergen |
    08:35 --- 20:38 | ...``.  That direct origin/destination should be kept
    as the product route.  Do not use this for long ``Route: Oslo to Myrdal,
    Myrdal to Flåm...`` descriptions, where the first internal leg would be
    misleading as the whole product route.
    """

    value = str(text or "")
    pipe_route = re.search(
        r"\|\s*([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)\s*\|",
        value,
        flags=re.IGNORECASE,
    )
    if pipe_route:
        origin = _clean_nutshell_place(pipe_route.group(1))
        destination = _clean_nutshell_place(pipe_route.group(2))
        if origin and destination and origin.lower() != destination.lower():
            return origin, destination

    prefix_route = re.search(
        r"^\s*([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)\s*\|\s*Norway\s+in\s+a\s+Nutshell",
        value,
        flags=re.IGNORECASE,
    )
    if prefix_route:
        origin = _clean_nutshell_place(prefix_route.group(1))
        destination = _clean_nutshell_place(prefix_route.group(2))
        if origin and destination and origin.lower() != destination.lower():
            return origin, destination

    return "", ""


def _norway_nutshell_route_label(text, fallback_origin="", fallback_destination=""):
    direct_origin, direct_destination = _direct_nutshell_pipe_route(str(text or ""))
    if direct_origin and direct_destination:
        return f"Norway in a Nutshell from {direct_origin} to {direct_destination}"

    explicit_destination_match = re.search(
        r"\bnorway\s+in\s+a\s+nutshell\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ ]+?)(?:\s+norway\s+in\s+a\s+nutshell|\s+-\s+|\s+\|\s+|$)",
        str(text or ""),
        flags=re.IGNORECASE,
    )
    if explicit_destination_match:
        destination = polish_title(explicit_destination_match.group(1).strip())
        if fallback_origin and fallback_origin.lower() != destination.lower():
            return f"Norway in a Nutshell from {polish_title(fallback_origin)} to {destination}"
        return f"Norway in a Nutshell to {destination}"

    origin, destination = fallback_origin, fallback_destination
    if origin and destination and origin.lower() != destination.lower():
        return f"Norway in a Nutshell from {origin} to {destination}"
    if destination:
        return f"Norway in a Nutshell to {destination}"
    return "Norway in a Nutshell"


def extract_norway_nutshell_route_points(text: str) -> list[str]:
    """Return a clean stop list from Nutshell timetable or route text.

    The itinerary should present the route as premium prose/list text, not with
    visual arrow glyphs. Timetable lines such as ``08:30 - 22:30`` are skipped
    so the end time cannot be misread as a route stop.
    """

    source = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    points: list[str] = []

    def add_point(value: str) -> None:
        place = _clean_nutshell_place(value)
        if not place or not re.search(r"[A-Za-zÀ-ÿøØåÅäÄöÖ]", place):
            return
        if place.lower() in {"norway in a nutshell", "including luggage porter service", "luggage porter service"}:
            return
        if not points or points[-1].lower() != place.lower():
            points.append(place)

    # Explicit pipe product route, e.g. "Norway in a Nutshell | Bergen to Oslo |".
    origin, destination = _direct_nutshell_pipe_route(source)

    # Timetable rows, e.g. "08:29 Bergen" / "22:27 Oslo".
    for raw in source.replace("|", "\n").splitlines():
        line = raw.strip()
        match = re.match(r"^\s*\d{1,2}:\d{2}\s*(?:am|pm)?\s+(.+)$", line, flags=re.IGNORECASE)
        if not match:
            continue
        place = match.group(1).strip(" -:|,.")
        # Skip pure time-range cells such as "08:30 - 22:30".
        if re.match(r"^[-–—]?\s*\d{1,2}:\d{2}\s*(?:am|pm)?\s*$", place, flags=re.IGNORECASE):
            continue
        place = re.split(r"\s+via\s+|\s+Via\s+", place, maxsplit=1)[0].strip(" -:|,.")
        place = re.sub(r"\s+Norway\s+in\s+a\s+Nutshell.*$", "", place, flags=re.IGNORECASE).strip(" -:|,.")
        add_point(place)

    if len(points) >= 2:
        return points

    # Narrative route text, e.g. "Route: Oslo to Myrdal by train, Myrdal to Flåm...".
    route_match = re.search(r"\broute\s*:\s*(.+?)(?:\bIncludes?\s*:|\bIncluded\s+journey\s*:|$)", source, flags=re.IGNORECASE | re.DOTALL)
    if route_match:
        route_text = route_match.group(1)
        for origin_match, dest_match in re.findall(
            r"([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)(?:\s+by\b|,|$)",
            route_text,
            flags=re.IGNORECASE,
        ):
            add_point(origin_match)
            add_point(dest_match)
        if len(points) >= 2:
            return points

    if origin and destination:
        return [origin, destination]
    return points


def format_norway_nutshell_route(points: list[str]) -> str:
    """Return a premium no-arrow route phrase."""

    clean_points: list[str] = []
    for point in points or []:
        place = _clean_nutshell_place(point)
        if place and (not clean_points or clean_points[-1].lower() != place.lower()):
            clean_points.append(place)
    if not clean_points:
        return ""
    if len(clean_points) == 1:
        return clean_points[0]
    if len(clean_points) == 2:
        return f"{clean_points[0]} to {clean_points[1]}"
    return f"{', '.join(clean_points[:-1])} and {clean_points[-1]}"


def has_norway_in_a_nutshell(rows):
    text = " ".join(f'{row.get("title", "")} {row.get("details", "")}' for row in rows).lower()
    return "norway in a nutshell" in text

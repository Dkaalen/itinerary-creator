"""Norway in a Nutshell transport detection and labels."""

from __future__ import annotations

import re

from text_polish import polish_title
from place_aliases import canonicalize_place_name


def _is_norway_in_a_nutshell_text(text):
    lower = str(text or "").lower()
    if re.search(r"norway\s+in\s+a\s+(?:nutshell|nuthsell)", lower):
        return True
    has_flam = any(marker in lower for marker in ["flåm", "flam", "flåmsbana", "flamsbana", "flåm train", "flam train", "flåm railway", "flam railway"])
    has_fjord = any(marker in lower for marker in ["nærøyfjord", "naeroyfjord", "fjord cruise", "gudvangen", "voss"])
    has_route_mode = bool(re.search(r"\b(?:train|rail|scenic\s+bus|bus|cruise)\b", lower))
    return (has_flam and has_fjord) or ("gudvangen" in lower and "voss" in lower and has_route_mode)


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
        r"^\s*([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)\s*\|\s*Norway\s+in\s+a\s+(?:Nutshell|Nuthsell)",
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
    source = str(text or "")
    direct_origin, direct_destination = _direct_nutshell_pipe_route(source)
    if direct_origin and direct_destination:
        return f"Norway in a Nutshell from {direct_origin} to {direct_destination}"

    explicit_destination_match = re.search(
        r"\bnorway\s+in\s+a\s+(?:nutshell|nuthsell)\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ ]+?)(?:\s+norway\s+in\s+a\s+(?:nutshell|nuthsell)|\s+-\s+|\s+\|\s+|$)",
        source,
        flags=re.IGNORECASE,
    )
    if explicit_destination_match:
        destination = polish_title(explicit_destination_match.group(1).strip())
        return f"Norway in a Nutshell to {destination}"

    # Product titles may include supplier service words before the real route,
    # e.g. "Nærøyfjord Cruise & Luggage Transfer Bergen to Oslo: Day Tour...".
    # Prefer a clean main city pair over the generic from/to extractor, which
    # can otherwise swallow the supplier prefix as part of the origin.
    city_names = "Bergen|Oslo|Flåm|Flam|Voss|Myrdal|Gudvangen"
    main_route_match = re.search(
        rf"(?:luggage\s+transfer\s+)?\b(?P<origin>{city_names})\s+to\s+(?P<destination>{city_names})\b",
        source,
        flags=re.IGNORECASE,
    )
    if main_route_match:
        origin = _clean_nutshell_place(main_route_match.group("origin"))
        destination = _clean_nutshell_place(main_route_match.group("destination"))
        if origin and destination and origin.lower() != destination.lower():
            return f"Norway in a Nutshell from {origin} to {destination}"

    origin, destination = fallback_origin, fallback_destination
    if origin and destination and origin.lower() != destination.lower():
        return f"Norway in a Nutshell from {origin} to {destination}"
    if destination:
        return f"Norway in a Nutshell to {destination}"
    return "Norway in a Nutshell"


def _normalise_nutshell_line_separators(text: str) -> str:
    """Repair common supplier separator typos inside timetable legs."""

    value = str(text or "")
    # Common typo/OCR issue: ``Myrdal 0 22:27 Oslo`` should be a dash
    # separator between departure place and arrival time.
    value = re.sub(r"(?<=[A-Za-zÀ-ÿøØåÅäÄöÖ])\s+0\s+(?=\d{1,2}:\d{2})", " - ", value)
    return value


def _format_leg_time(value: str) -> str:
    text = str(value or "").strip()
    match = re.fullmatch(r"(\d{1,2}):(\d{2})\s*(am|pm)?", text, flags=re.IGNORECASE)
    if not match:
        return text
    hour = int(match.group(1))
    minute = match.group(2)
    suffix = (match.group(3) or "").upper()
    if suffix:
        if suffix == "PM" and hour < 12:
            hour += 12
        elif suffix == "AM" and hour == 12:
            hour = 0
    display_hour = hour % 12 or 12
    display_suffix = "AM" if hour < 12 else "PM"
    return f"{display_hour}:{minute} {display_suffix}"



def _clean_nutshell_mode(value: str) -> str:
    mode = polish_title(str(value or "").strip(" .-:|,"))
    mode = re.sub(r"^Via\s+", "", mode, flags=re.IGNORECASE)
    mode = re.sub(r"\bNorway\s+in\s+a\s+(?:Nutshell|Nuthsell).*$", "", mode, flags=re.IGNORECASE).strip(" .-:|,")
    if mode.lower() == "scenic bus":
        return "Scenic Bus"
    if mode.lower() == "scenic train":
        return "Scenic Train"
    if mode.lower() == "train":
        return "Train"
    if mode.lower() == "bus":
        return "Bus"
    if mode.lower() == "cruise":
        return "Cruise"
    return mode


def _time_place_points(source: str) -> list[dict[str, str]]:
    """Extract single-line timetable points such as ``09:18 Oslo``.

    Some supplier Norway in a Nutshell rows are pasted as alternating departure
    and arrival lines rather than one full leg per line. Pairing those points in
    order keeps route days structured instead of becoming generic activities.
    """

    points: list[dict[str, str]] = []
    point_pattern = re.compile(
        r"^\s*(?P<time>\d{1,2}:\d{2}\s*(?:am|pm)?)\s+(?P<place>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)(?:\s+via\s+(?P<mode>[^|,;]+))?\s*$",
        flags=re.IGNORECASE,
    )
    for raw in source.replace("|", "\n").splitlines():
        line = raw.strip(" .")
        match = point_pattern.match(line)
        if not match:
            continue
        place = _clean_nutshell_place(match.group("place"))
        if not place:
            continue
        points.append({
            "time": _format_leg_time(match.group("time")),
            "place": place,
            "mode": _clean_nutshell_mode(match.group("mode") or ""),
        })
    return points


def _paired_nutshell_route_legs(source: str) -> list[dict[str, str]]:
    points = _time_place_points(source)
    if len(points) < 2 or len(points) % 2 != 0:
        return []
    # Only pair alternating lines when the arrival rows carry transport mode
    # evidence ("via train", "via scenic bus", etc.). Plain timetable stop
    # lists are better rendered as route highlights.
    if not any(point.get("mode") for point in points[1::2]):
        return []
    legs: list[dict[str, str]] = []
    for index in range(0, len(points), 2):
        departure = points[index]
        arrival = points[index + 1]
        if departure["place"].lower() == arrival["place"].lower():
            return []
        legs.append({
            "departure_time": departure["time"],
            "origin": departure["place"],
            "arrival_time": arrival["time"],
            "destination": arrival["place"],
            "mode": arrival.get("mode", ""),
        })
    return legs

def extract_norway_nutshell_route_legs(text: str) -> list[dict[str, str]]:
    """Return clean timetable legs for Norway in a Nutshell rows."""

    source = _normalise_nutshell_line_separators(str(text or "").replace("\r\n", "\n").replace("\r", "\n"))
    legs: list[dict[str, str]] = []
    leg_pattern = re.compile(
        r"^\s*(?P<dep>\d{1,2}:\d{2}\s*(?:am|pm)?)\s+(?P<origin>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)\s*[-–—]\s*(?P<arr>\d{1,2}:\d{2}\s*(?:am|pm)?)\s+(?P<destination>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)(?:\s+via\s+(?P<mode>[^|,;]+))?\s*$",
        flags=re.IGNORECASE,
    )
    for raw in source.replace("|", "\n").splitlines():
        line = raw.strip(" .")
        match = leg_pattern.match(line)
        if not match:
            continue
        origin = _clean_nutshell_place(match.group("origin"))
        destination = _clean_nutshell_place(match.group("destination"))
        if not origin or not destination:
            continue
        mode = _clean_nutshell_mode(match.group("mode") or "")
        legs.append({
            "departure_time": _format_leg_time(match.group("dep")),
            "origin": origin,
            "arrival_time": _format_leg_time(match.group("arr")),
            "destination": destination,
            "mode": mode,
        })
    return legs or _paired_nutshell_route_legs(source)

def extract_norway_nutshell_route_points(text: str) -> list[str]:
    """Return a clean stop list from Nutshell timetable or route text.

    The itinerary should present the route as premium prose/list text, not with
    visual arrow glyphs. Timetable lines such as ``08:30 - 22:30`` are skipped
    so the end time cannot be misread as a route stop.
    """

    source = _normalise_nutshell_line_separators(str(text or "").replace("\r\n", "\n").replace("\r", "\n"))
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

    for leg in extract_norway_nutshell_route_legs(source):
        add_point(leg.get("origin", ""))
        add_point(leg.get("destination", ""))
    if len(points) >= 2:
        return points

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
        place = re.sub(r"\s+Norway\s+in\s+a\s+(?:Nutshell|Nuthsell).*$", "", place, flags=re.IGNORECASE).strip(" -:|,.")
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

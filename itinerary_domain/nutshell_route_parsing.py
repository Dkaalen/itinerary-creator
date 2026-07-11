"""Route and supplier-include parsing for Norway in a Nutshell products."""

from __future__ import annotations

import re

from text_polish import polish_title
from itinerary_domain.nutshell_cleaning import _clean_place as _clean_nutshell_place


def _split_supplier_inclusion_items(value: str) -> list[str]:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\btranfser\b", "transfer", text, flags=re.IGNORECASE)
    parts = [part.strip(" -•;.") for part in re.split(r"\s*(?:,|;|\n|\u2022)\s*", text) if part.strip(" -•;.")]
    return parts


def extract_norway_nutshell_supplier_includes(row_or_text) -> list[str]:
    """Return source-faithful included route legs for Nutshell rows."""

    if isinstance(row_or_text, dict):
        values = [
            str(row_or_text.get("raw_text") or ""),
            str(row_or_text.get("raw") or ""),
            str(row_or_text.get("details") or ""),
            str(row_or_text.get("description_raw") or ""),
            str(row_or_text.get("original_title") or ""),
            str(row_or_text.get("title") or ""),
        ]
        source = "\n".join(value for value in values if value.strip())
    else:
        source = str(row_or_text or "")

    include_match = re.search(
        r"\bincludes?\s*:\s*(?P<items>.*?)(?=\s+-\s+(?:description|notes?|meeting\s+point|time|duration)\s*:|\s+description\s*:|$)",
        source,
        flags=re.IGNORECASE | re.DOTALL,
    )
    raw_items = include_match.group("items") if include_match else ""
    if not raw_items and isinstance(row_or_text, dict):
        includes = row_or_text.get("source_includes") or row_or_text.get("supplier_includes") or row_or_text.get("includes") or []
        if isinstance(includes, str):
            raw_items = includes
        else:
            raw_items = "\n".join(str(item) for item in includes or [])

    route_items: list[str] = []
    for item in _split_supplier_inclusion_items(raw_items):
        clean = polish_title(item).replace("Tranfser", "Transfer")
        clean = re.sub(r"\btrain\s+transfer\b", "Train transfer", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\bcoach\s+transfer\b", "Coach Transfer", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\bfjord\s+cruise\b", "Fjord Cruise", clean, flags=re.IGNORECASE)
        has_route = re.search(r"\b[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+\s+to\s+[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+\b", clean, flags=re.IGNORECASE)
        has_mode = re.search(r"\b(?:train|rail|railway|fjord\s+cruise|cruise|coach|bus|transfer)\b", clean, flags=re.IGNORECASE)
        generic_catalogue = clean.lower() in {"bergen railway", "flåm railway", "flam railway", "fjord cruise", "scenic bus journey"}
        product_title_fragment = bool(re.search(r"\bday\s+tour\b.*\b(?:incl|including)\b", clean, flags=re.IGNORECASE))
        if has_route and has_mode and not generic_catalogue and not product_title_fragment and clean not in route_items:
            route_items.append(clean)
    return route_items


def _direct_nutshell_pipe_route(text: str) -> tuple[str, str]:
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


def _normalise_nutshell_line_separators(text: str) -> str:
    value = str(text or "")
    return re.sub(r"(?<=[A-Za-zÀ-ÿøØåÅäÄöÖ])\s+0\s+(?=\d{1,2}:\d{2})", " - ", value)


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


def _add_nutshell_point(points: list[str], value: str) -> None:
    place = _clean_nutshell_place(value)
    if not place or not re.search(r"[A-Za-zÀ-ÿøØåÅäÄöÖ]", place):
        return
    if place.lower() in {"norway in a nutshell", "including luggage porter service", "luggage porter service"}:
        return
    if not points or points[-1].lower() != place.lower():
        points.append(place)


def _route_points_from_timetable_legs(source: str, points: list[str]) -> list[str]:
    for leg in extract_norway_nutshell_route_legs(source):
        _add_nutshell_point(points, leg.get("origin", ""))
        _add_nutshell_point(points, leg.get("destination", ""))
    return points


def _route_points_from_supplier_includes(source: str, points: list[str]) -> list[str]:
    for item in extract_norway_nutshell_supplier_includes(source):
        route_match = re.search(
            r"\b(?P<origin>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)\s+to\s+(?P<destination>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)\s*$",
            item,
            flags=re.IGNORECASE,
        )
        if not route_match:
            continue
        origin = route_match.group("origin")
        destination = route_match.group("destination")
        origin = re.sub(r"^(?:train\s+transfer|train|rail|railway|flåm\s+railway|flam\s+railway|fjord\s+cruise|cruise|coach\s+transfer|coach|bus\s+transfer|bus)\s+", "", origin, flags=re.IGNORECASE).strip(" -:|,")
        _add_nutshell_point(points, origin)
        _add_nutshell_point(points, destination)
    return points


def _route_points_from_timetable_rows(source: str, points: list[str]) -> list[str]:
    for raw in source.replace("|", "\n").splitlines():
        line = raw.strip()
        match = re.match(r"^\s*\d{1,2}:\d{2}\s*(?:am|pm)?\s+(.+)$", line, flags=re.IGNORECASE)
        if not match:
            continue
        place = match.group(1).strip(" -:|,.")
        if re.match(r"^[-–—]?\s*\d{1,2}:\d{2}\s*(?:am|pm)?\s*$", place, flags=re.IGNORECASE):
            continue
        place = re.split(r"\s+via\s+|\s+Via\s+", place, maxsplit=1)[0].strip(" -:|,.")
        place = re.sub(r"\s+Norway\s+in\s+a\s+(?:Nutshell|Nuthsell).*$", "", place, flags=re.IGNORECASE).strip(" -:|,.")
        _add_nutshell_point(points, place)
    return points


def _route_points_from_narrative_route(source: str, points: list[str]) -> list[str]:
    route_match = re.search(r"\broute\s*:\s*(.+?)(?:\bIncludes?\s*:|\bIncluded\s+journey\s*:|$)", source, flags=re.IGNORECASE | re.DOTALL)
    if not route_match:
        return points
    route_text = route_match.group(1)
    for origin_match, dest_match in re.findall(
        r"([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)(?:\s+by\b|,|$)",
        route_text,
        flags=re.IGNORECASE,
    ):
        _add_nutshell_point(points, origin_match)
        _add_nutshell_point(points, dest_match)
    return points


def extract_norway_nutshell_route_points(text: str) -> list[str]:
    """Return a clean stop list from Nutshell timetable or route text."""

    source = _normalise_nutshell_line_separators(str(text or "").replace("\r\n", "\n").replace("\r", "\n"))
    points: list[str] = []
    origin, destination = _direct_nutshell_pipe_route(source)

    for collector in (
        _route_points_from_timetable_legs,
        _route_points_from_supplier_includes,
        _route_points_from_timetable_rows,
        _route_points_from_narrative_route,
    ):
        collector(source, points)
        if len(points) >= 2:
            return points

    if origin and destination:
        return [origin, destination]
    return points

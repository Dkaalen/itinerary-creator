"""Low-level Norway in a Nutshell source parsing helpers."""

from __future__ import annotations

import re

from text_polish import polish_title
from place_aliases import canonicalize_place_name


def _is_norway_in_a_nutshell_text(text):
    lower = str(text or "").lower()
    if re.search(r"norway\s+in\s+a\s+(?:nutshell|nuthsell)", lower):
        return True
    # Do not infer this branded product from ordinary Flåm/Gudvangen/Voss
    # rail, coach and fjord rows.  Those can be independent scenic services.
    return False


def is_source_backed_nutshell_route_package(text: str) -> bool:
    """Return True for a complete source-backed Nutshell-style route package.

    This is intentionally narrower than generic Flåm/Nærøyfjord detection: it
    requires a major Oslo/Bergen route heading and the supplier-owned chain of
    rail, fjord and luggage/ticket evidence.
    """

    source = str(text or "")
    lower = source.lower()
    if _is_norway_in_a_nutshell_text(source):
        return True
    direct_major_route = bool(
        re.search(
            r"(?:^|\b)(?P<origin>Oslo|Bergen)\s+to\s+(?P<destination>Oslo|Bergen)\s*(?=[:|\-]|$)",
            source,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    )
    if not direct_major_route:
        return False

    has_flam_rail = any(marker in lower for marker in ("flåm train", "flam train", "flåm railway", "flam railway"))
    has_fjord = "nærøyfjord" in lower or "naeroyfjord" in lower or "fjord cruise" in lower
    has_supplier_chain = all(
        marker in lower
        for marker in (
            "voss",
            "gudvangen",
            "flåm",
            "myrdal",
        )
    ) or all(marker in lower for marker in ("voss", "gudvangen", "flam", "myrdal"))
    has_ticketed_route = any(marker in lower for marker in ("e-tickets", "e tickets", "all tickets", "luggage transfer", "luggage porter"))
    has_day_route_context = bool(re.search(r"\bday\s+tour\b|\btravel\s+plan\b|\bperfect\s+day\s+tour\b", lower))
    return has_flam_rail and has_fjord and has_supplier_chain and has_ticketed_route and has_day_route_context


def _clean_nutshell_place(value: str) -> str:
    return canonicalize_place_name(polish_title(str(value or "").strip(" -:|.,")))


NUTSHELL_ROUTE_PLACES = "Bergen|Oslo|Flåm|Flam|Voss|Gudvangen|Myrdal|Geilo"
# Myrdal is normally an interchange station on the Flåm Railway leg.
# Gudvangen and Voss are not globally blocked: Fjord Tours supports route starts/ends
# and overnight extensions in real route villages, so they may be valid titles when
# supplier title, route endpoint or accommodation context supports them.
NUTSHELL_INTERCHANGE_ONLY_NODES = {"myrdal"}


def explicit_norway_nutshell_title(text: str) -> str:
    """Return the supplier's explicit Nutshell title when present.

    Norway in a Nutshell is a route product. The supplier-written title
    destination must win over route-leg text. Places such as Gudvangen and
    Voss can be valid starts, ends or overnight stops; they are only wrong
    when promoted from an included intermediate leg over a clearer title.
    """

    source = str(text or "")
    full_route = re.search(
        r"\bnorway\s+in\s+a\s+(?:nutshell|nuthsell)\s+from\s+(?P<origin>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)\s+to\s+(?P<destination>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)(?=\s+-\s+|\s+\|\s+|\s+time\s*:|\s+meeting\s+point\s*:|\s+includes?\s*:|\s+description\s*:|$)",
        source,
        flags=re.IGNORECASE,
    )
    if full_route:
        origin = _clean_nutshell_place(full_route.group("origin"))
        destination = _clean_nutshell_place(full_route.group("destination"))
        if origin and destination and origin.lower() != destination.lower():
            return f"Norway in a Nutshell from {origin} to {destination}"

    match = re.search(
        r"\bnorway\s+in\s+a\s+(?:nutshell|nuthsell)\s+to\s+(?P<destination>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)(?=\s+-\s+|\s+\|\s+|\s+time\s*:|\s+meeting\s+point\s*:|\s+includes?\s*:|\s+description\s*:|$)",
        source,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    destination = _clean_nutshell_place(match.group("destination"))
    return f"Norway in a Nutshell to {destination}" if destination else ""


def explicit_norway_nutshell_destination(text: str) -> str:
    title = explicit_norway_nutshell_title(text)
    match = re.search(r"\bto\s+(.+)$", title)
    return match.group(1).strip() if match else ""


def is_nutshell_internal_route_node(place: str) -> bool:
    clean = _clean_nutshell_place(place).lower()
    return clean in NUTSHELL_INTERCHANGE_ONLY_NODES


def _split_supplier_inclusion_items(value: str) -> list[str]:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\btranfser\b", "transfer", text, flags=re.IGNORECASE)
    parts = [part.strip(" -•;.") for part in re.split(r"\s*(?:,|;|\n|\u2022)\s*", text) if part.strip(" -•;.")]
    return parts


def extract_norway_nutshell_supplier_includes(row_or_text) -> list[str]:
    """Return source-faithful included route legs for Nutshell rows.

    These are supplier inclusions, not catalogue template labels.  They are
    intentionally preserved so a row saying ``Train transfer Oslo to Myrdal``
    does not become only ``Bergen Railway`` in client output.
    """

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
        # Fallback for rows where the parser already split inclusions but kept
        # route-shaped supplier wording there.  Generic catalogue labels are
        # filtered below.
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




def should_preserve_nutshell_origin_label(source: str, origin: str = "", destination: str = "") -> bool:
    """Return True when a Nutshell label should keep ``from X to Y`` wording."""

    source_text = str(source or "")
    origin_clean = _clean_nutshell_place(origin).lower()
    destination_clean = _clean_nutshell_place(destination).lower()
    if re.search(r"\bnorway\s+in\s+a\s+(?:nutshell|nuthsell)\s+from\s+", source_text, flags=re.IGNORECASE):
        return True
    if re.search(r"\|\s*[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+\s+to\s+[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+\s*\|", source_text):
        return True
    if "luggage" in source_text.lower() and ("porter" in source_text.lower() or "transfer" in source_text.lower() or "service" in source_text.lower()):
        return True
    major_endpoints = {"oslo", "bergen"}
    return bool(origin_clean in major_endpoints and destination_clean in major_endpoints and origin_clean != destination_clean)


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

    # Source-faithful supplier includes, e.g. "Fjord Cruise Flåm to Gudvangen,
    # Coach Transfer Gudvangen to Voss, Train transfer Voss to Bergen".
    # These route legs may be all we have when the supplier title is generic;
    # use the complete chain endpoint, never the first included waypoint alone.
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
        add_point(origin)
        add_point(destination)
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

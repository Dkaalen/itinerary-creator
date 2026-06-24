"""Canonical route extraction helpers for transport rows."""

from __future__ import annotations

import re

from parser_modules.common import extract_route_points
from place_aliases import canonicalize_place_name
from text_polish import polish_client_text
from itinerary_generation.transport_model import get_transport_source_text
from itinerary_generation.transport_safety import normalize_transport_place


_ROUTE_PREFIX_ORIGINS = {
    "transfer", "train transfer", "scenic train transfer", "flight transfer",
    "coach transfer", "bus transfer", "long distance panorama coach transfer",
    "panoramic coach transfer", "coastal cruise", "overnight coastal cruise",
    "overnight cruise", "cruise", "atlantic ocean cruise", "ferry transfer",
    "arrival", "overnight train", "train", "norway in a nutshell",
}


def _transport_source_text(row):
    """Backward-compatible wrapper for shared transport source text."""

    return get_transport_source_text(row)




def _explicit_transport_route_from_source(source_text: str) -> tuple[str, str]:
    """Extract direction from compact supplier route titles before generic parsing.

    Generic route parsing can mistake timing phrases such as ``to next day
    arrival`` for a destination.  Route transport titles usually state the real
    direction immediately after the mode: ``Overnight Cruise Stockholm to
    Tallinn`` or ``Tallinn to Helsinki 2 Hr cruise``.
    """

    source = str(source_text or "")
    place = r"[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?"
    known_places = r"(?:Copenhagen|København|Gothenburg|Göteborg|Oslo|Stockholm|Helsinki|Tallinn|Tallin|Bergen|Reykjavík|Reykjavik|Rovaniemi|Tromsø|Tromso|Alta|Gudvangen|Voss|Flåm|Flam|Myrdal)"
    patterns = [
        rf"\b(?:day\s+)?(?:train|flight|coach|bus|cruise|ferry)\s*[:,]?\s*(?P<origin>{known_places})\s*[-–—]\s*(?P<destination>{known_places})(?=\s*(?:\n|intercity\b|ic\b|train\b|flight\b|coach\b|bus\b|cruise\b|ferry\b|\d{{1,2}}:\d{{2}}|$))",
        rf"\b(?:(?:overnight|night)\s+)?(?:cruise|ferry|train|flight|coach|bus)\s*[:,]?\s*(?P<origin>{place})\s+to\s+(?P<destination>{place})(?:\s*\||\s+-\s+|\s+\d{{1,2}}(?::|\s|$)|\s+self[-\s]*arranged|\s+self\s+arranged|\s+cost\s+not|\s*,?\s*tickets?\s+to\s+be\s+bought|\s*,?\s*tickets?\s+to\s+be\s+purchased|,|$)",
        rf"\b(?P<origin>{place})\s+to\s+(?P<destination>{place})\s+(?:\d+\s*(?:hr|hrs|hour|hours)\s+)?(?:cruise|ferry|train|flight|coach|bus)\b",
        rf"\b(?P<origin>{place})\s+to\s+(?P<destination>{place})\s*\|",
        rf"\b(?:train|flight|coach|bus|cruise|ferry)\s+(?P<origin>{known_places})\s+(?P<destination>{known_places})\b",
        rf"\b(?P<origin>{known_places})\s+to\s+(?P<destination>{known_places})\s+(?:train|flight|coach|bus|cruise|ferry)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, source, flags=re.IGNORECASE)
        if not match:
            continue
        origin = _clean_route_place(match.group("origin"))
        destination = _clean_route_place(match.group("destination"))
        if origin and destination and origin.lower() != destination.lower():
            return origin, destination
    return "", ""

def _clean_route_place(value):
    raw = str(value or "").strip(" -:|.,")
    raw = re.sub(
        r"^(?:long[-\s]*distance\s+comfortable\s+panorama\s+coach\s+transfer|long[-\s]*distance\s+panorama\s+coach\s+transfer|panoramic\s+coach\s+transfer|panorama\s+coach\s+transfer|coach\s+transfer|bus\s+transfer|transfer)\s+from\s+",
        "",
        raw,
        flags=re.IGNORECASE,
    ).strip(" -:|.,")
    raw = re.sub(r"^(?:from|to)\s+", "", raw, flags=re.IGNORECASE).strip(" -:|.,")
    raw = re.sub(r"\bself[-\s]*(?:arranged|arrange|arrnaged|arrnage)\b", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\b(?:cost|price)\s+not\s+in(?:cl|lc)uded\b", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\bnot\s+included\b", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*,?\s*tickets?\s+to\s+be\s+(?:bought|purchased).*$", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*,?\s*to\s+be\s+paid\s+locally.*$", "", raw, flags=re.IGNORECASE)
    raw = re.split(
        r"\s+-\s+(?:\d+\s*x\s*)?(?:private\s+)?(?:sleeper|sleeping)\s+(?:compartment|cabin|berth)|\s+-\s+breakfast\s+included|\s+-\s+train\s+ticket\s+included",
        raw,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" -:|.,")
    # Common supplier typo: "Saariselka t to Rovaniemi" leaves a stray
    # trailing "t" on the origin after route splitting. Do not let that
    # become a client-facing place name.
    raw = re.sub(r"\s+\bt\b$", "", raw, flags=re.IGNORECASE).strip(" -:|.,")
    raw = re.split(r"\s+-\s+|\s+\|\s+|\s+via\s+|\s+at\s+\d{1,2}:\d{2}|\s+\d{1,2}:\d{2}", raw, maxsplit=1, flags=re.IGNORECASE)[0].strip(" -:|.,")
    if re.search(r"\s+to\s+", raw, flags=re.IGNORECASE):
        raw = re.split(r"\s+to\s+", raw, flags=re.IGNORECASE)[-1].strip(" -:|.,")
    raw = re.sub(r"\bKakslaut+?enen\s+Arctic\s+Resort\b", "Kakslauttanen", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\bKakslauttanen\s+Arctic\s+Resort\b", "Kakslauttanen", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\bRovaneimi\b", "Rovaniemi", raw, flags=re.IGNORECASE)
    if re.search(r"fl[åa]msbanen", raw, flags=re.IGNORECASE):
        raw = "Flåm"
    if re.search(r"one[- ]?way geiranger fjord cruise", raw, flags=re.IGNORECASE):
        raw = "Ålesund"
    place = normalize_transport_place(canonicalize_place_name(raw) or raw)
    lower = place.lower()
    invalid_places = _ROUTE_PREFIX_ORIGINS | {
        "",
        "the",
        "hotel",
        "the hotel",
        "station",
        "the station",
        "airport",
        "the airport",
        "accommodation",
        "your accommodation",
        "your hotel",
        "ticket counter",
        "be bought on spot at ticket counter",
        "be bought on site at ticket counter",
        "next day",
        "arrival next day",
        "arrives next day",
    }
    if lower in invalid_places:
        return ""
    blocked_phrases = ["santa claus express", "downstairs cabin", "tickets included", "ticket to be bought", "ticket to be purchased", "ticket counter", "on spot", "on site", "meal plan", "wc in carriage", "women's", "men's", "benefits", "made bed", "sleeping compartment", "overnight train"]
    if any(marker in lower for marker in blocked_phrases):
        return ""
    if re.search(r"\b(?:shower|sink)\b", lower):
        return ""
    return place



def _scheduled_route_points_from_source(source_text: str) -> tuple[str, str]:
    """Extract first departure place and final arrival place from timetable prose."""

    source = str(source_text or "")
    departures = re.findall(
        r"\bdeparture\s+from\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)\s*:",
        source,
        flags=re.IGNORECASE,
    )
    arrivals = re.findall(
        r"\barrival\s+in\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)\s*:",
        source,
        flags=re.IGNORECASE,
    )
    if departures and arrivals:
        origin = _clean_route_place(departures[0])
        destination = _clean_route_place(arrivals[-1])
        if origin and destination and origin.lower() != destination.lower():
            return origin, destination
    return "", ""

def get_route_points_for_transport(row):
    """Return normalized (origin, destination) for a transport row.

    This is route-based rather than fixture-based. It looks across title,
    details and original text, because supplier cells often put the route in
    any of those locations.
    """
    source_text = _transport_source_text(row)

    scheduled_origin, scheduled_destination = _scheduled_route_points_from_source(source_text)
    if scheduled_destination:
        return scheduled_origin, scheduled_destination

    for key in ["details", "original_title", "raw", "title"]:
        explicit_origin, explicit_destination = _explicit_transport_route_from_source(str(row.get(key, "") or ""))
        if explicit_destination:
            return explicit_origin, explicit_destination

    explicit_from_to_match = re.search(
        r"\bfrom\s+(.+?)\s+to\s+(.+?)(?:\s+-\s+|\s+\|\s+|$)",
        source_text,
        flags=re.IGNORECASE,
    )
    if explicit_from_to_match:
        origin = _clean_route_place(explicit_from_to_match.group(1))
        destination = _clean_route_place(explicit_from_to_match.group(2))
        if destination:
            return origin, destination


    dash_route_pattern = re.compile(
        r"\b(?:train|night\s+train|overnight\s+train|scenic\s+train|flight|coach|bus|ferry|cruise)(?:\s+transfer)?\s*:?\s*([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)\s+-\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)\s+-\s+(?:\d{1,2}:\d{2}|tickets?|car\s+ticket|train\s+ticket|coach\s+ticket|luggage|meal|included|$)",
        flags=re.IGNORECASE,
    )
    for key in ["details", "original_title", "title"]:
        dash_route_match = dash_route_pattern.search(str(row.get(key, "") or ""))
        if dash_route_match:
            origin = _clean_route_place(dash_route_match.group(1))
            destination = _clean_route_place(dash_route_match.group(2))
            if destination:
                return origin, destination

    station_match = re.search(r"\b([A-Za-zÀ-ÿøØåÅäÄöÖ ]+?)\s+(?:Central|station)\s*[–-]\s*([A-Za-zÀ-ÿøØåÅäÄöÖ ]+?)\s+station\b", source_text, flags=re.IGNORECASE)
    if station_match:
        return _clean_route_place(station_match.group(1)), _clean_route_place(station_match.group(2))

    plain_from_match = re.search(r"\bfrom\s+([A-Za-zÀ-ÿøØåÅäÄöÖ ]+?)\s+(?:Central|station)\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ ]+?)\s+(?:Central|station)\b", source_text, flags=re.IGNORECASE)
    if plain_from_match:
        return _clean_route_place(plain_from_match.group(1)), _clean_route_place(plain_from_match.group(2))

    # Prefer the parser-normalized title for destination, but enrich it with
    # origin from supplier details when the destination matches. This avoids
    # stale contradictory details while still producing useful route wording.
    title_origin, title_destination = extract_route_points(str(row.get("title", "") or ""))
    title_origin = _clean_route_place(title_origin)
    title_destination = _clean_route_place(title_destination)
    if title_destination:
        for key in ["details", "original_title"]:
            origin, destination = extract_route_points(str(row.get(key, "") or ""))
            origin = _clean_route_place(origin)
            destination = _clean_route_place(destination)
            if origin and destination and destination.lower() == title_destination.lower():
                return origin, title_destination
        row_type = str(row.get("effective_type") or row.get("type") or "")
        title_lower = str(row.get("title", "") or "").lower()
        city_origin = _clean_route_place(row.get("city", ""))
        if city_origin and city_origin.lower() != title_destination.lower() and (row_type in {"Cruise", "Ferry"} or "cruise" in title_lower or "ferry" in title_lower):
            return city_origin, title_destination
        return title_origin, title_destination

    for key in ["details", "original_title"]:
        origin, destination = extract_route_points(str(row.get(key, "") or ""))
        origin = _clean_route_place(origin)
        destination = _clean_route_place(destination)
        if destination:
            return origin, destination

    origin, destination = extract_route_points(_transport_source_text(row))
    origin = _clean_route_place(origin)
    destination = _clean_route_place(destination)
    if destination:
        return origin, destination

    return "", _clean_route_place(row.get("city", ""))



def _scheduled_via_points_from_source(source_text: str, origin: str = "", destination: str = "") -> list[str]:
    """Return intermediate arrival places from timetable prose."""

    source = str(source_text or "")
    arrivals = re.findall(
        r"\barrival\s+in\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)\s*:",
        source,
        flags=re.IGNORECASE,
    )
    points: list[str] = []
    for raw in arrivals[:-1]:
        candidate = _clean_route_place(raw)
        if candidate and candidate.lower() not in {origin.lower(), destination.lower()} and candidate not in points:
            points.append(candidate)
    return points[:2]

def get_route_via_points(row, origin="", destination=""):
    text = polish_client_text(_transport_source_text(row))
    points = _scheduled_via_points_from_source(text, origin, destination)
    if points:
        return points

    for via_match in re.finditer(r"\bvia\s+([A-Za-zÀ-ÿøØåÅäÄöÖ\s]+?)(?:\s+-\s+|\s+\||,|$)", text, flags=re.IGNORECASE):
        candidate = _clean_route_place(via_match.group(1))
        if candidate and candidate.lower() not in {origin.lower(), destination.lower()} and candidate not in points:
            points.append(candidate)

    # Multi-leg phrasing such as Copenhagen to Malmö to Stockholm.
    route_match = re.search(r"\b(?:train|scenic train transfer|flight|coach|bus|ferry|cruise)(?:\s+transfer)?\s*[:|]?\s*(.+?\s+to\s+.+?)(?:\s+-\s+(?:departure|arrival|time|includes|included|excludes)\b|$)", text, flags=re.IGNORECASE)
    if route_match:
        route_text = route_match.group(1)
        pieces = [_clean_route_place(piece) for piece in re.split(r"\s+to\s+", route_text, flags=re.IGNORECASE)]
        pieces = [piece for piece in pieces if piece]
        if len(pieces) > 2:
            for piece in pieces[1:-1]:
                if piece.lower() not in {origin.lower(), destination.lower()} and piece not in points:
                    points.append(piece)

    if not points and re.search(r"\bmalm[øo]\b", text, flags=re.IGNORECASE) and destination.lower() != "malmö":
        points.append("Malmö")

    return points[:2]


def _via_suffix(via_points):
    if not via_points:
        return ""
    return ", via " + " and ".join(via_points)


def _route_destination_from_text(value):
    text = polish_client_text(value)
    if not text or " to " not in text.lower():
        return ""
    _, destination = extract_route_points(text)
    return canonicalize_place_name(destination) if destination else ""

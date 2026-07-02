"""Canonical route extraction helpers for transport rows."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

from parser_modules.common import extract_route_points
from place_aliases import canonicalize_place_name
from text_polish import polish_client_text
from itinerary_generation.transport_model import get_transport_source_text
from itinerary_generation.transport_safety import normalize_transport_place


@dataclass(frozen=True)
class TransportRouteFacts:
    """Canonical route facts for one transport row.

    Titles, inclusions and renderers should consume these facts instead of
    reparsing supplier text independently.  The confidence value is a small
    source hint for callers/tests; it is not shown to clients.
    """

    origin: str = ""
    destination: str = ""
    via: tuple[str, ...] = field(default_factory=tuple)
    mode: str = ""
    supplier_hints: tuple[str, ...] = field(default_factory=tuple)
    confidence: str = ""

    @property
    def has_route(self) -> bool:
        return bool(self.origin and self.destination)


_ROUTE_PREFIX_ORIGINS = {
    "transfer", "train transfer", "scenic train transfer", "flight transfer",
    "coach transfer", "bus transfer", "long distance panorama coach transfer",
    "panoramic coach transfer", "coastal cruise", "overnight coastal cruise",
    "overnight cruise", "cruise", "atlantic ocean cruise", "ferry transfer",
    "arrival", "overnight train", "train", "flight", "norway in a nutshell",
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
        rf"\b(?P<origin>{known_places})\s*:\s*(?:(?:scenic|panoramic|long[-\s]*distance|coastal|atlantic\s+ocean|overnight)\s+)*(?:train|flight|coach|bus|cruise|ferry)(?:\s+transfer)?\s+to\s+(?P<destination>{place})(?:\s*,?\s+via\b|\s+-\s+|\s+\|\s+|,|$)",
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


def _strip_transport_product_prefix(raw: str) -> str:
    """Remove service/product words that supplier rows can glue to origins."""

    text = str(raw or "").strip(" -:|.,")
    mode = r"(?:flight|train|coach|bus|cruise|ferry|rail)"
    transfer_mode = r"(?:coach|bus|train|flight|ferry|cruise)?\s*transfer"
    product_words = (
        r"(?:domestic|international|regional|scheduled|direct|connecting|"
        r"overnight|night|day|sleeper|scenic|coastal|eurostar|intercity|ic|"
        r"long[-\s]*distance|comfortable|panorama|panoramic|atlantic\s+ocean)"
    )

    text = re.sub(
        rf"^(?:{product_words}\s+){{0,6}}(?:{mode}|{transfer_mode})(?:\s+transfer)?\s+from\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" -:|.,")
    text = re.sub(
        rf"^(?:{product_words}\s+){{1,6}}(?:{mode}|{transfer_mode})(?:\s+transfer)?\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" -:|.,")
    text = re.sub(
        r"^(?:flight|train|coach|cruise|ferry|bus(?!\s+(?:station|terminal|stop)\b))\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" -:|.,")
    text = re.sub(
        rf"^(?:long[-\s]*distance\s+comfortable\s+panorama\s+coach\s+transfer|long[-\s]*distance\s+panorama\s+coach\s+transfer|panoramic\s+coach\s+transfer|panorama\s+coach\s+transfer|coach\s+transfer|bus\s+transfer|transfer)\s+from\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" -:|.,")
    return text


def _clean_route_place(value):
    raw = _strip_transport_product_prefix(str(value or ""))
    raw = re.sub(r"^(?:from|to)\s+", "", raw, flags=re.IGNORECASE).strip(" -:|.,")
    raw = re.sub(r"\bself[-\s]*(?:arranged|arrange|arrnaged|arrnage)\b", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\b(?:cost|price)\s+not\s+in(?:cl|lc)uded\b", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\bnot\s+included\b", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*,?\s*tickets?\s+to\s+be\s+(?:bought|purchased).*$", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*,?\s*to\s+be\s+paid\s+locally.*$", "", raw, flags=re.IGNORECASE)
    raw = re.split(
        r"\s+-\s+(?:\d+\s*x\s*)?(?:private\s+)?(?:sleeper|sleeping)\s+(?:compartment|cabin|berth)|\s+-\s+breakfast\s+included|\s+-\s+train\s+ticket\s+included|\s+onboard\s+",
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
        "to",
        "from",
        "hotel",
        "the hotel",
        "station",
        "the station",
        "airport",
        "the airport",
        "ticket",
        "tickets",
        "ticket costs",
        "travel costs",
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



def _row_city_origin(row) -> str:
    return _clean_route_place(row.get("city", ""))


def _expanded_transfer_route_from_title(title: str) -> tuple[str, str]:
    """Extract routes from already-normalized client transfer titles.

    These titles are safer than concatenated title/details/raw text.  Parsing a
    combined source such as ``Private transfer from Helsinki Railway Station to
    Helsinki Airport Private Station to the airport`` can otherwise glue a
    duplicate shorthand fragment onto the destination.
    """

    match = re.search(
        r"\b(?:private\s+)?(?:shuttle\s+)?transfer\s+from\s+(.+?)\s+to\s+(.+?)$",
        str(title or ""),
        flags=re.IGNORECASE,
    )
    if not match:
        return "", ""
    origin = _clean_route_place(match.group(1))
    destination = _clean_route_place(match.group(2))
    if origin and destination and origin.lower() != destination.lower():
        return origin, destination
    return "", ""


def _headline_route_from_source(value: str) -> tuple[str, str]:
    """Prefer a supplier headline route before itemized leg text.

    Package rows often start with a true end-to-end route (``Bergen to Oslo:``)
    and later list individual tickets (``Voss to Gudvangen``).  The headline is
    the client-facing route identity; the itemized legs remain supporting facts.
    """

    text = str(value or "")
    match = re.search(
        r"^\s*(?P<origin>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,40})\s+to\s+(?P<destination>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,40})(?:\s*:|\s+-|\s*\|)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return "", ""
    origin = _clean_route_place(match.group("origin"))
    destination = _clean_route_place(match.group("destination"))
    if origin and destination and origin.lower() != destination.lower():
        return origin, destination
    return "", ""


def _compact_city_terminal_route(row, value: str) -> tuple[str, str]:
    """Expand compact city-owned terminal routes such as ``Private Station to Airport``."""

    city = _clean_route_place(row.get("city", ""))
    if not city:
        return "", ""
    text = str(value or "")
    lower = text.lower()
    if re.search(r"\bprivate\s+(?:transfer\s+)?(?:railway\s+)?station\s+to\s+(?:the\s+)?airport\b", lower):
        return normalize_transport_place(f"{city} Railway Station"), normalize_transport_place(f"{city} Airport")
    if re.search(r"\bprivate\s+(?:transfer\s+)?airport\s+to\s+(?:hotel|accommodation)\b", lower):
        return normalize_transport_place(f"{city} Airport"), "your accommodation"
    if re.search(r"\bprivate\s+(?:transfer\s+)?(?:hotel|accommodation)\s+to\s+(?:the\s+)?airport\b", lower):
        return "your hotel", normalize_transport_place(f"{city} Airport")
    if re.search(r"\bprivate\s+(?:transfer\s+)?(?:hotel|accommodation)\s+to\s+(?:railway\s+)?station\b", lower):
        return "your hotel", normalize_transport_place(f"{city} Railway Station")
    if re.search(r"\bprivate\s+(?:transfer\s+)?(?:railway\s+)?station\s+to\s+(?:hotel|accommodation)\b", lower):
        return normalize_transport_place(f"{city} Railway Station"), "your accommodation"
    return "", ""


def _explicit_product_route_from_row_city(row) -> tuple[str, str]:
    """Handle product-style titles such as 'Nærøyfjord Cruise to Flåm'.

    Normalized titles can collapse supplier context to generic labels such as
    ``Cruise to Flåm``.  Use the source-owned title/details before the cleaned
    title so route extraction does not mistake the product name for the origin.
    """

    row_type = str(row.get("effective_type") or row.get("type") or "")
    if row_type not in {"Cruise", "Ferry", "Train", "Coach", "Transport"}:
        return "", ""
    source_candidates = [
        str(row.get("original_title") or ""),
        str(row.get("details") or ""),
        str(row.get("raw") or ""),
        str(row.get("title") or ""),
    ]
    pattern = re.compile(
        r"\b(?:n[æa]r[øo]yfjord|fjord|coastal|sightseeing|scenic|fl[åa]msbanen)\s+(?:cruise|train|rail|ferry)\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)(?:\s+-|\s+time\s*:|\s+includes?\s*:|$)",
        flags=re.IGNORECASE,
    )
    for source in source_candidates:
        match = pattern.search(source)
        if not match:
            continue
        origin = _row_city_origin(row)
        destination = _clean_route_place(match.group(1))
        if origin and destination and origin.lower() != destination.lower():
            return origin, destination
    return "", ""


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

def _get_route_points_for_transport_uncached(row):
    """Return normalized (origin, destination) for a transport row.

    This is route-based rather than fixture-based. It looks across title,
    details and original text, because supplier cells often put the route in
    any of those locations.
    """
    source_text = _transport_source_text(row)

    product_origin, product_destination = _explicit_product_route_from_row_city(row)
    if product_destination:
        return product_origin, product_destination

    scheduled_origin, scheduled_destination = _scheduled_route_points_from_source(source_text)
    if scheduled_destination:
        return scheduled_origin, scheduled_destination

    title_origin, title_destination = _expanded_transfer_route_from_title(str(row.get("title", "") or ""))
    if title_destination:
        return title_origin, title_destination

    for key in ["original_title", "details", "title"]:
        headline_origin, headline_destination = _headline_route_from_source(str(row.get(key, "") or ""))
        if headline_destination:
            return headline_origin, headline_destination

    for key in ["details", "original_title", "raw", "title"]:
        compact_origin, compact_destination = _compact_city_terminal_route(row, str(row.get(key, "") or ""))
        if compact_destination:
            return compact_origin, compact_destination

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
        if city_origin and city_origin.lower() != title_destination.lower() and (
            row_type in {"Flight", "Cruise", "Ferry", "Train"}
            or "flight" in title_lower or "cruise" in title_lower or "ferry" in title_lower or "train" in title_lower
        ):
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



def _route_row_signature(row) -> tuple[str, ...]:
    if not isinstance(row, dict):
        return (str(row),)
    return (
        str(row.get("row_id") or row.get("line_number") or ""),
        str(row.get("type") or ""),
        str(row.get("effective_type") or ""),
        str(row.get("city") or ""),
        str(row.get("title") or ""),
        str(row.get("original_title") or ""),
        str(row.get("details") or ""),
        str(row.get("raw") or row.get("raw_text") or ""),
        str(row.get("route_origin") or ""),
        str(row.get("route_destination") or ""),
    )


def _row_from_route_signature(signature: tuple[str, ...]) -> dict:
    if len(signature) == 1:
        return {"title": signature[0]}
    (
        row_id,
        row_type,
        effective_type,
        city,
        title,
        original_title,
        details,
        raw,
        route_origin,
        route_destination,
    ) = signature
    return {
        "row_id": row_id,
        "type": row_type,
        "effective_type": effective_type,
        "city": city,
        "title": title,
        "original_title": original_title,
        "details": details,
        "raw": raw,
        "route_origin": route_origin,
        "route_destination": route_destination,
    }


@lru_cache(maxsize=2048)
def _cached_route_points_for_transport(signature: tuple[str, ...]) -> tuple[str, str]:
    return _get_route_points_for_transport_uncached(_row_from_route_signature(signature))


def get_route_points_for_transport(row):
    """Return normalized (origin, destination) for a transport row."""

    return _cached_route_points_for_transport(_route_row_signature(row))

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


def _transport_mode_for_row(row: dict) -> str:
    row_type = str(row.get("effective_type") or row.get("type") or "").strip()
    source = _transport_source_text(row).lower()
    if row_type == "Flight" or "flight" in source:
        return "flight"
    if row_type == "Train" or re.search(r"\b(?:train|rail|eurostar)\b", source):
        return "train"
    if row_type in {"Coach", "Bus"} or re.search(r"\b(?:coach|bus)\b", source):
        return "coach"
    if row_type == "Ferry" or "ferry" in source:
        return "ferry"
    if row_type == "Cruise" or "cruise" in source:
        return "cruise"
    if row_type == "Transfer" or "transfer" in source:
        return "transfer"
    return row_type.lower()


def get_transport_route_facts(row: dict) -> TransportRouteFacts:
    """Return the canonical transport route facts for titles/rendering/inclusions."""

    origin, destination = get_route_points_for_transport(row)
    via = tuple(get_route_via_points(row, origin, destination) or ())
    mode = _transport_mode_for_row(row)
    confidence = "explicit" if origin and destination else ("destination_only" if destination else "")
    hints = tuple(
        hint
        for hint in (
            "via" if via else "",
            "source_route" if origin and destination else "",
        )
        if hint
    )
    return TransportRouteFacts(
        origin=origin,
        destination=destination,
        via=via,
        mode=mode,
        supplier_hints=hints,
        confidence=confidence,
    )


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

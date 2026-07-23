"""Route-place cleaning helpers for transport route extraction."""

from __future__ import annotations

import re

from place_aliases import canonicalize_place_name
from itinerary_generation.transport_safety import normalize_transport_place

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


def strip_transport_product_prefix(raw: str) -> str:
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


def clean_route_place(value):
    raw = strip_transport_product_prefix(str(value or ""))
    raw = re.sub(r"^(?:from|to)\s+", "", raw, flags=re.IGNORECASE).strip(" -:|.,")
    raw = re.sub(r"\bself[-\s]*(?:arranged|arrange|arrnaged|arrnage)\b", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\b(?:cost|price)\s+not\s+in(?:cl|lc)uded\b", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\bnot\s+included\b", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*,?\s*tickets?\s+to\s+be\s+(?:bought|purchased).*$", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*,?\s*tickets?\b.*$", "", raw, flags=re.IGNORECASE)
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
    # Parsers can retain a dangling schedule preposition after stripping the
    # actual time (for example ``Bergen at``). It is not part of the place.
    raw = re.sub(r"\s+\b(?:at|on)\b$", "", raw, flags=re.IGNORECASE).strip(" -:|.,")
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



def canonical_route_city(name: object) -> str:
    """Return a client-safe canonical spelling for common route cities."""

    clean = str(name or "").strip()
    replacements = {
        "saariselka": "Saariselkä",
        "kakslauttenen": "Kakslauttanen",
        "tromso": "Tromsø",
        "svolvaer": "Svolvær",
        "svolaver": "Svolvær",
        "gothernburg": "Gothenburg",
        "göteborg": "Gothenburg",
        "malmo": "Malmø",
    }
    return replacements.get(clean.lower(), clean)

# Backward-compatible private aliases for legacy import paths.
_strip_transport_product_prefix = strip_transport_product_prefix
_clean_route_place = clean_route_place

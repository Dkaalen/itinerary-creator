"""Low-level Norway in a Nutshell source parsing helpers."""

from __future__ import annotations

import re

from text_polish import polish_title
from place_aliases import canonicalize_place_name
from itinerary_domain.nutshell_route_parsing import (
    extract_norway_nutshell_route_legs,
    extract_norway_nutshell_route_points,
    extract_norway_nutshell_supplier_includes,
)


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
    has_full_supplier_chain = all(
        marker in lower
        for marker in (
            "voss",
            "gudvangen",
            "flåm",
            "myrdal",
        )
    ) or all(marker in lower for marker in ("voss", "gudvangen", "flam", "myrdal"))
    has_endpoint_backed_chain = (
        direct_major_route
        and "gudvangen" in lower
        and "myrdal" in lower
        and ("flåm" in lower or "flam" in lower)
    )
    has_ticketed_route = any(marker in lower for marker in ("e-tickets", "e tickets", "all tickets", "luggage transfer", "luggage porter"))
    has_day_route_context = bool(re.search(r"\bday\s+tour\b|\btravel\s+plan\b|\bperfect\s+day\s+tour\b", lower))
    return (
        has_flam_rail
        and has_fjord
        and (has_full_supplier_chain or has_endpoint_backed_chain)
        and has_ticketed_route
        and has_day_route_context
    )


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

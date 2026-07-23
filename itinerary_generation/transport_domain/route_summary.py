"""Route-summary helpers owned by the transport domain.

Day intro writers need compact origin/destination/mode facts, but the logic
that extracts those facts should stay close to transport parsing.  These
helpers are prose-free and return route facts only.
"""

from __future__ import annotations

import re
from typing import Mapping, Sequence

from itinerary_generation.common_constants import TRANSPORT_TYPES
from itinerary_generation.row_filters import get_row_type
from itinerary_generation.transport_domain.route_cleaning import canonical_route_city, clean_route_place
from itinerary_generation.transport_detection import is_route_transfer
from itinerary_generation.transport_domain.routes import get_route_points_for_transport
from itinerary_generation.transport_domain.titles import get_transfer_travel_title
from itinerary_generation.transport_safety import base_destination_from_terminal
from parser_modules.common import extract_route_points
from text_polish import polish_title


_SERVICE_ENDPOINT_RE = re.compile(
    r"^(?:private|shared|self[- ]?arranged)?\s*(?:airport\s+)?(?:transfer|transport|journey|travel)$",
    re.IGNORECASE,
)
_SERVICE_PLACE_FRAGMENT_RE = re.compile(
    r"\b(?:overnight\s+)?(?:cruise|flight|train|railway|coach|bus|ferry)(?:\s+transfer)?\b",
    re.IGNORECASE,
)
_TRANSPORT_HUB_RE = re.compile(
    r"\b(?:airport|station|terminal|bus\s+stop|ferry\s+port|cruise\s+port|harbou?r|port|pier|dock)\b",
    re.IGNORECASE,
)
_SOURCE_CITY_PREFIX_RE = re.compile(r"^\s*([A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{1,45})\s*:")


def _place_endpoint(value: object) -> str:
    endpoint = clean_route_place(str(value or ""))
    if not endpoint or _SERVICE_ENDPOINT_RE.fullmatch(endpoint):
        return ""
    if _SERVICE_PLACE_FRAGMENT_RE.search(endpoint) and not _TRANSPORT_HUB_RE.search(endpoint):
        return ""
    return canonical_route_city(endpoint)


def _source_city_prefix(row: Mapping[str, object]) -> str:
    for key in ("details", "original_title", "raw", "raw_text"):
        match = _SOURCE_CITY_PREFIX_RE.search(str(row.get(key, "") or ""))
        if not match:
            continue
        city = _place_endpoint(match.group(1))
        if city:
            return city
    return ""


def _nutshell_contract_endpoints(row: Mapping[str, object]) -> tuple[str, str]:
    product = row.get("activity_product")
    if not isinstance(product, Mapping):
        return "", ""
    contract = product.get("domain_contract")
    if not isinstance(contract, Mapping) or contract.get("kind") != "norway_in_a_nutshell_journey":
        return "", ""
    destination = _place_endpoint(contract.get("destination"))
    origin = _place_endpoint(contract.get("origin"))
    city = _place_endpoint(row.get("city"))
    if not origin and city and (not destination or city.casefold() != destination.casefold()):
        origin = city
    return origin, destination


def transport_endpoints_from_row(row: Mapping[str, object]) -> tuple[str, str]:
    """Return place endpoints for one transport row.

    The low-level route parser can encounter service phrases such as
    ``Private transfer`` before a real ``to Airport`` destination.  Consumer
    layers need place facts, not transport labels, so those false endpoints are
    removed once at this domain boundary.
    """

    contract_origin, contract_destination = _nutshell_contract_endpoints(row)
    if contract_destination:
        return contract_origin, contract_destination

    origin, destination = get_route_points_for_transport(dict(row))
    clean_origin, clean_destination = _place_endpoint(origin), _place_endpoint(destination)
    if not clean_origin and clean_destination:
        source_city = _source_city_prefix(row)
        if source_city and source_city.casefold() != clean_destination.casefold():
            clean_origin = source_city
    return clean_origin, clean_destination


def transport_destination_from_row(row: Mapping[str, object]) -> str:
    """Return the raw destination endpoint for one transport row."""

    _origin, destination = transport_endpoints_from_row(row)
    return destination


def has_transport_endpoints(row: Mapping[str, object]) -> bool:
    """Return true when a row has both origin and destination endpoints."""

    origin, destination = transport_endpoints_from_row(row)
    return bool(origin and destination)


def summarize_route_from_rows(day_rows: Sequence[Mapping[str, object]]) -> tuple[str, str, str]:
    """Return origin, destination and main mode for route-led day intros."""

    origin = ""
    destination = ""
    mode = ""
    for row in day_rows:
        row_dict = dict(row)
        row_type = get_row_type(row_dict)
        if row_type not in TRANSPORT_TYPES:
            continue
        if not mode:
            row_text = f'{row_dict.get("title", "")} {row_dict.get("details", "")} {row_dict.get("original_title", "")}'.lower()
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
        route_origin, route_destination = get_route_points_for_transport(row_dict)
        if route_origin and not origin:
            origin = canonical_route_city(base_destination_from_terminal(route_origin) or route_origin)
        if route_destination:
            destination = canonical_route_city(base_destination_from_terminal(route_destination) or route_destination)
    return origin, destination, mode


def infer_route_endpoints_from_title(title: str, city: str = "") -> tuple[str, str]:
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


def infer_travel_mode_from_title(title: str) -> str:
    """Infer a coarse transport mode from a planned day title."""

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

_INVALID_TRAVEL_DESTINATION_WORDS = {
    "hotel",
    "station",
    "airport",
    "accommodation",
    "your accommodation",
    "self transfer",
    "private airport to hotel",
    "private hotel to airport",
}
_BAD_DESTINATION_FRAGMENTS = ("shower", "sink", "wc", "benefits", "made bed")


def destination_city_from_travel_rows(day_rows: Sequence[Mapping[str, object]]) -> str:
    """Return the clearest destination city from route transport rows."""

    travel_rows = [
        dict(row)
        for row in day_rows
        if get_row_type(dict(row)) in TRANSPORT_TYPES
        or get_row_type(dict(row)) == "Transfer"
        or is_route_transfer(dict(row))
    ]
    destination_city = ""
    for row in travel_rows:
        route_destination = ""
        if get_row_type(row) in TRANSPORT_TYPES:
            _, route_destination = get_route_points_for_transport(row)
        if not route_destination and is_route_transfer(row):
            _, route_destination = extract_route_points(get_transfer_travel_title(row))
        candidate = str(route_destination or "").strip()
        lower_candidate = candidate.lower()
        if candidate and lower_candidate not in _INVALID_TRAVEL_DESTINATION_WORDS and not any(
            bad in lower_candidate for bad in _BAD_DESTINATION_FRAGMENTS
        ):
            destination_city = canonical_route_city(base_destination_from_terminal(candidate) or candidate)
            continue
        title_match = re.search(
            r"\bto\s+([A-Za-zÀ-ÿøØåÅäÄöÖ]+(?:\s+[A-Za-zÀ-ÿøØåÅäÄöÖ]+)?)\s*$",
            str(row.get("title", "")),
            flags=re.IGNORECASE,
        )
        if title_match and title_match.group(1).lower() not in _INVALID_TRAVEL_DESTINATION_WORDS:
            destination_city = canonical_route_city(base_destination_from_terminal(title_match.group(1)) or title_match.group(1))
    return destination_city


__all__ = [
    "destination_city_from_travel_rows",
    "infer_route_endpoints_from_title",
    "infer_travel_mode_from_title",
    "has_transport_endpoints",
    "summarize_route_from_rows",
    "transport_destination_from_row",
    "transport_endpoints_from_row",
]

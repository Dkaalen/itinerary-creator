"""Row-aware route endpoint inference and precedence."""
from __future__ import annotations

import re

from parser_modules.common import extract_route_points
from itinerary_generation.transport_domain.route_hubs import (
    _explicit_transport_route_from_source,
    clean_route_place as _clean_route_place,
)
from itinerary_generation.transport_domain.route_validation import _canonical_route_field_is_place
from itinerary_generation.transport_model import get_transport_source_text
from itinerary_generation.transport_safety import normalize_transport_place

def _transport_source_text(row):
    return get_transport_source_text(row)


def _row_city_origin(row) -> str:
    return _clean_route_place(row.get("city", ""))


def _expanded_transfer_route_from_title(title: str) -> tuple[str, str]:
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
    city = _clean_route_place(row.get("city", ""))
    if not city:
        return "", ""
    lower = str(value or "").lower()
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


def _route_from_canonical_fields(row) -> tuple[str, str]:
    """Return plausible parser-normalized route truth before text inference."""

    raw_origin = str(row.get("route_origin", "") or "").strip()
    raw_destination = str(row.get("route_destination", "") or "").strip()
    if not raw_destination or not _canonical_route_field_is_place(raw_destination):
        return "", ""
    if raw_origin and not _canonical_route_field_is_place(raw_origin):
        return "", ""

    origin = _clean_route_place(raw_origin)
    destination = _clean_route_place(raw_destination)
    if not destination:
        return "", ""
    if origin and origin.casefold() == destination.casefold():
        return "", ""
    return origin, destination


def _route_from_self_drive_row(row) -> tuple[str, str]:
    """Use the row city as origin for imperative self-drive titles."""

    row_type = str(row.get("effective_type") or row.get("type") or "")
    if row_type != "Drive":
        return "", ""
    origin = _row_city_origin(row)
    for key in ("title", "original_title", "details"):
        _parsed_origin, destination = extract_route_points(str(row.get(key, "") or ""))
        destination = _clean_route_place(destination)
        if origin and destination and origin.casefold() != destination.casefold():
            return origin, destination
    return "", ""



def _branded_service_route_from_source(value: str) -> tuple[str, str]:
    """Extract ``service name + origin to destination`` route headlines.

    Named services such as ``Santa Claus Express Helsinki to Rovaniemi``
    contain a product label before the real origin. Generic route parsing can
    mistake the full label for a place, so the service noun is the boundary.
    """

    place = r"[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?"
    match = re.search(
        rf"\b(?:[A-Za-zÀ-ÿøØåÅäÄöÖ'-]+\s+){{0,4}}"
        rf"(?:express|line|railway|train|flight|cruise|ferry|coach|bus)\s+"
        rf"(?P<origin>{place})\s+to\s+(?P<destination>{place})"
        rf"(?:\s+-\s+|\s+\|\s+|,|$)",
        str(value or ""),
        flags=re.IGNORECASE,
    )
    if not match:
        return "", ""
    origin = _clean_route_place(match.group("origin"))
    destination = _clean_route_place(match.group("destination"))
    if origin and destination and origin.casefold() != destination.casefold():
        return origin, destination
    return "", ""

def _route_from_structured_transport_sources(row, source_text: str) -> tuple[str, str]:
    for origin, destination in (
        _explicit_product_route_from_row_city(row),
        _scheduled_route_points_from_source(source_text),
        _branded_service_route_from_source(str(row.get("original_title", "") or "")),
        _branded_service_route_from_source(str(row.get("title", "") or "")),
        _expanded_transfer_route_from_title(str(row.get("title", "") or "")),
    ):
        if destination:
            return origin, destination

    for key in ["original_title", "details", "title"]:
        headline_origin, headline_destination = _headline_route_from_source(str(row.get(key, "") or ""))
        if headline_destination:
            return headline_origin, headline_destination
    return "", ""


def _route_from_explicit_transport_fields(row, source_text: str) -> tuple[str, str]:
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
    return "", ""


def _route_from_dash_or_station_patterns(row, source_text: str) -> tuple[str, str]:
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
    return "", ""


def _route_from_title_with_source_origin(row) -> tuple[str, str]:
    title_origin, title_destination = extract_route_points(str(row.get("title", "") or ""))
    title_origin = _clean_route_place(title_origin)
    title_destination = _clean_route_place(title_destination)
    if not title_destination:
        return "", ""

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
        row_type in {"Flight", "Cruise", "Ferry", "Train", "Drive"}
        or "flight" in title_lower
        or "cruise" in title_lower
        or "ferry" in title_lower
        or "train" in title_lower
        or title_lower.startswith("drive ")
    ):
        return city_origin, title_destination
    return title_origin, title_destination


def _route_from_unstructured_fallbacks(row) -> tuple[str, str]:
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


def _validated_route_candidate(row, origin: str, destination: str) -> tuple[str, str]:
    """Validate every extractor candidate before it becomes route truth.

    Individual extractors are intentionally permissive recall mechanisms. This
    boundary prevents service labels such as ``on the Bergen Line`` or
    ``transfer on the Northern Lights Express`` from becoming places. When a
    destination is sound but the proposed origin is not, the workbook row city
    is the strongest available replacement.
    """

    clean_destination = _clean_route_place(destination)
    if not clean_destination or not _canonical_route_field_is_place(clean_destination):
        return "", ""

    clean_origin = _clean_route_place(origin)
    if clean_origin and not _canonical_route_field_is_place(clean_origin):
        clean_origin = ""
    if not clean_origin:
        row_type = str(row.get("effective_type") or row.get("type") or "")
        if row_type != "Transfer":
            city_origin = _row_city_origin(row)
            if city_origin and _canonical_route_field_is_place(city_origin):
                clean_origin = city_origin
    if clean_origin and clean_origin.casefold() == clean_destination.casefold():
        clean_origin = ""
    return clean_origin, clean_destination


def _get_route_points_for_transport_uncached(row):
    source_text = _transport_source_text(row)
    for resolver in (
        lambda: _route_from_canonical_fields(row),
        lambda: _route_from_self_drive_row(row),
        lambda: _route_from_structured_transport_sources(row, source_text),
        lambda: _route_from_explicit_transport_fields(row, source_text),
        lambda: _route_from_dash_or_station_patterns(row, source_text),
        lambda: _route_from_title_with_source_origin(row),
        lambda: _route_from_unstructured_fallbacks(row),
    ):
        origin, destination = _validated_route_candidate(row, *resolver())
        if destination:
            return origin, destination
    return "", ""


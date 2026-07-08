"""Canonical route extraction helpers for transport rows."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from parser_modules.common import extract_route_points
from place_aliases import canonicalize_place_name
from text_polish import polish_client_text
from itinerary_generation.transport_domain.route_cleaning import (
    _ROUTE_PREFIX_ORIGINS,
    clean_route_place as _clean_route_place,
)
from itinerary_generation.transport_domain.route_points import get_route_points_for_transport
from itinerary_generation.transport_model import get_transport_source_text


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


def _transport_source_text(row):
    """Backward-compatible wrapper for shared transport source text."""

    return get_transport_source_text(row)


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

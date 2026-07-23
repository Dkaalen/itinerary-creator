"""Intermediate-stop extraction for transport routes."""
from __future__ import annotations

import re

from text_polish import polish_client_text
from itinerary_generation.transport_domain.route_hubs import clean_route_place as _clean_route_place
from itinerary_generation.transport_domain.route_validation import _canonical_route_field_is_place
from itinerary_generation.transport_model import get_transport_source_text


def _transport_source_text(row):
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
        if candidate and _canonical_route_field_is_place(candidate) and candidate.lower() not in {origin.lower(), destination.lower()} and candidate not in points:
            points.append(candidate)
    return points[:2]


def get_route_via_points(row, origin="", destination=""):
    text = polish_client_text(_transport_source_text(row))
    points = _scheduled_via_points_from_source(text, origin, destination)
    if points:
        return points

    for via_match in re.finditer(r"\bvia\s+([A-Za-zÀ-ÿøØåÅäÄöÖ\s]+?)(?:\s+-\s+|\s+\||,|$)", text, flags=re.IGNORECASE):
        candidate = _clean_route_place(via_match.group(1))
        if candidate and _canonical_route_field_is_place(candidate) and candidate.lower() not in {origin.lower(), destination.lower()} and candidate not in points:
            points.append(candidate)

    for connection_match in re.finditer(
        r"\b(?:with\s+)?connection\s+in\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)(?:\s+to\s+|\s+-\s+|\s+\||,|$)",
        text,
        flags=re.IGNORECASE,
    ):
        candidate = _clean_route_place(connection_match.group(1))
        if candidate and _canonical_route_field_is_place(candidate) and candidate.lower() not in {origin.lower(), destination.lower()} and candidate not in points:
            points.append(candidate)

    # Multi-leg phrasing such as Copenhagen to Malmö to Stockholm.
    route_match = re.search(r"\b(?:train|scenic train transfer|flight|coach|bus|ferry|cruise)(?:\s+transfer)?\s*[:|]?\s*(.+?\s+to\s+.+?)(?:\s+-\s+(?:departure|arrival|time|includes|included|excludes)\b|$)", text, flags=re.IGNORECASE)
    if route_match:
        route_text = route_match.group(1)
        pieces = [_clean_route_place(piece) for piece in re.split(r"\s+to\s+", route_text, flags=re.IGNORECASE)]
        pieces = [piece for piece in pieces if piece]
        if len(pieces) > 2:
            for piece in pieces[1:-1]:
                if _canonical_route_field_is_place(piece) and piece.lower() not in {origin.lower(), destination.lower()} and piece not in points:
                    points.append(piece)

    if not points and re.search(r"\bmalm[øo]\b", text, flags=re.IGNORECASE) and destination.lower() != "malmö":
        points.append("Malmö")

    return points[:2]


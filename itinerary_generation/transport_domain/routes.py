"""Canonical route extraction helpers for transport rows."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from parser_modules.common import extract_route_points
from place_aliases import canonicalize_place_name
from text_polish import polish_client_text
from itinerary_generation.transport_domain.route_hubs import (
    _ROUTE_PREFIX_ORIGINS,
    clean_route_place as _clean_route_place,
)
from itinerary_generation.transport_domain.route_intermediate_stops import get_route_via_points
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

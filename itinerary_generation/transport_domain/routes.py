"""Canonical route extraction helpers for transport rows."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from itinerary_domain.source_route_parsing import extract_route_points
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
    has_transport_mode: bool = False
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def has_route(self) -> bool:
        return bool(self.origin and self.destination)

    @property
    def display_route(self) -> str:
        """Return a compact client-safe route projection for QA and diagnostics."""

        if self.origin and self.destination:
            return f"{self.origin} to {self.destination}"
        return self.destination or self.origin


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


_SERVICE_ENDPOINT_RE = re.compile(
    r"^(?:shuttle transfer|self transfer|activity upgrade|transfer package)$",
    flags=re.IGNORECASE,
)
_TRANSPORT_OWNER_TYPES = frozenset(
    {"Transfer", "Transport", "Flight", "Train", "Coach", "Bus", "Ferry", "Cruise"}
)


def _endpoint_contract_warnings(row: dict, origin: str, destination: str) -> tuple[str, ...]:
    """Return diagnostics when raw endpoint fields contain service labels.

    Canonical route extraction may correctly discard those labels.  QA still
    needs to know that the source contract supplied a service phrase where a
    geographic endpoint was expected, without maintaining a second parser.
    """

    raw_origin = str(row.get("route_origin") or origin or "").strip(" -:|,.")
    raw_destination = str(row.get("route_destination") or destination or "").strip(" -:|,.")
    warnings: list[str] = []
    if _SERVICE_ENDPOINT_RE.fullmatch(raw_origin):
        warnings.append("origin_looks_like_service_phrase")
    if _SERVICE_ENDPOINT_RE.fullmatch(raw_destination):
        warnings.append("destination_looks_like_service_phrase")
    return tuple(warnings)


def _has_explicit_transport_mode(row: dict, mode: str) -> bool:
    """Return whether transport mode is owned by the row contract itself.

    Activity descriptions often mention included transfers.  Those logistical
    details may help route rendering, but they must not make QA classify the
    activity itself as a transport product.
    """

    row_type = str(row.get("effective_type") or row.get("type") or row.get("source_type") or "").strip()
    return bool(mode and row_type in _TRANSPORT_OWNER_TYPES)


def get_transport_route_facts(row: dict) -> TransportRouteFacts:
    """Return the canonical transport route facts for production and QA."""

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
        has_transport_mode=_has_explicit_transport_mode(row, mode),
        warnings=_endpoint_contract_warnings(row, origin, destination),
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

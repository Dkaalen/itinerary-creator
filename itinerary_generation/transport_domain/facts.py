"""Canonical transport facts for parser/generator/QA consumers.

This module is intentionally fact-only: it extracts route and mode signals from a
row, but it does not decide prose.  Consumers should prefer this model over
re-parsing raw transfer/title text in each layer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from parser_modules.place_parsing import extract_route_points, normalize_place_name
from shared.text import clean_space
from text_polish import polish_client_text

LOCAL_TRANSFER_RE = re.compile(
    r"\b(?:hotel|accommodation|airport|terminal|station|railway station|bus station|cruise terminal|harbou?r)\b",
    flags=re.IGNORECASE,
)
AIRPORT_TRANSFER_RE = re.compile(r"\bairport\b", flags=re.IGNORECASE)
TRANSIT_ONLY_RE = re.compile(r"\b(?:via|connection|transit|layover|change in)\b", flags=re.IGNORECASE)
MODE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("flight", re.compile(r"\bflight\b", re.IGNORECASE)),
    ("train", re.compile(r"\b(?:train|rail)\b", re.IGNORECASE)),
    ("ferry", re.compile(r"\bferry\b", re.IGNORECASE)),
    ("cruise", re.compile(r"\bcruise\b", re.IGNORECASE)),
    ("coach", re.compile(r"\b(?:coach|bus|arctic route)\b", re.IGNORECASE)),
    ("transfer", re.compile(r"\b(?:transfer|shuttle)\b", re.IGNORECASE)),
)


@dataclass(frozen=True)
class TransportFacts:
    mode: str = ""
    origin: str = ""
    destination: str = ""
    via: tuple[str, ...] = ()
    is_local_transfer: bool = False
    is_airport_transfer: bool = False
    is_transit_only: bool = False
    display_title: str = ""
    display_route: str = ""
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def has_route(self) -> bool:
        return bool(self.origin or self.destination)


def build_transport_facts(row: Mapping[str, Any] | None) -> TransportFacts:
    """Return normalized transport facts for one row-like mapping."""

    source = dict(row or {})
    row_type = _clean(source.get("effective_type") or source.get("type") or source.get("source_type"))
    title = _clean(source.get("title") or source.get("original_title") or "")
    details = _clean(source.get("details") or source.get("description") or "")
    city = _place(source.get("city") or "")
    text = clean_space(" ".join(part for part in (row_type, title, details) if part))
    mode = _detect_mode(row_type, title, details)
    origin, destination = extract_route_points(text)
    origin = _place(origin)
    destination = _place(destination)
    if not origin and mode == "transfer" and AIRPORT_TRANSFER_RE.search(text):
        origin = city if "from" in text.casefold() else ""
    if not destination and mode == "transfer" and AIRPORT_TRANSFER_RE.search(text):
        destination = _airport_label(city)
    warnings = tuple(_warnings(row_type, text, origin, destination))
    return TransportFacts(
        mode=mode,
        origin=origin,
        destination=destination,
        via=_via_points(text, origin, destination),
        is_local_transfer=mode == "transfer" and bool(LOCAL_TRANSFER_RE.search(text)),
        is_airport_transfer=bool(AIRPORT_TRANSFER_RE.search(text)),
        is_transit_only=bool(TRANSIT_ONLY_RE.search(text)) and not destination,
        display_title=_display_title(mode, origin, destination, title),
        display_route=_display_route(origin, destination),
        warnings=warnings,
    )


def _clean(value: object) -> str:
    return polish_client_text(str(value or "")).strip(" -:|,.")


def _place(value: object) -> str:
    return normalize_place_name(str(value or "").strip(" -:|,."))


def _detect_mode(row_type: str, title: str, details: str) -> str:
    combined = f"{row_type} {title} {details}"
    type_lower = row_type.casefold()
    if type_lower in {"flight", "train", "ferry", "cruise"}:
        return type_lower
    if type_lower in {"transfer", "transport", "coach", "bus"}:
        if type_lower in {"coach", "bus"}:
            return "coach"
        if type_lower == "transport":
            for mode, pattern in MODE_PATTERNS:
                if mode != "transfer" and pattern.search(combined):
                    return mode
        return "transfer" if type_lower == "transfer" else "transport"
    for mode, pattern in MODE_PATTERNS:
        if pattern.search(combined):
            return mode
    return ""


def _airport_label(city: str) -> str:
    return f"{city} Airport" if city else "the airport"


def _display_route(origin: str, destination: str) -> str:
    if origin and destination:
        return f"{origin} to {destination}"
    return destination or origin


def _display_title(mode: str, origin: str, destination: str, fallback: str) -> str:
    route = _display_route(origin, destination)
    if mode and route:
        label = "Coach transfer" if mode == "coach" else mode.capitalize()
        return f"{label} from {route}" if origin and destination and mode == "transfer" else f"{label} to {destination}" if destination and not origin else f"{label}: {route}"
    return fallback


def _via_points(text: str, origin: str, destination: str) -> tuple[str, ...]:
    via: list[str] = []
    for raw in re.findall(r"\bvia\s+([A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35})(?:\b|[,|.;])", text):
        place = _place(raw)
        if place and place.casefold() not in {origin.casefold(), destination.casefold()}:
            via.append(place)
    return tuple(dict.fromkeys(via))


def _warnings(row_type: str, text: str, origin: str, destination: str) -> list[str]:
    warnings: list[str] = []
    service_place = r"(?:shuttle transfer|self transfer|activity upgrade|transfer package)"
    if re.fullmatch(service_place, origin.strip(), flags=re.IGNORECASE):
        warnings.append("origin_looks_like_service_phrase")
    if re.fullmatch(service_place, destination.strip(), flags=re.IGNORECASE):
        warnings.append("destination_looks_like_service_phrase")
    if "activity" in row_type.casefold() and re.search(r"\b(?:transfer|coach|bus|train|flight|ferry)\b", text, flags=re.IGNORECASE):
        warnings.append("activity_type_has_transport_signal")
    return warnings


__all__ = ["TransportFacts", "build_transport_facts"]

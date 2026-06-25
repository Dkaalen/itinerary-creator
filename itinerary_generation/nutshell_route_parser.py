"""Norway in a Nutshell route endpoint and leg helpers."""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

from place_aliases import canonicalize_place_name

from itinerary_generation.nutshell_cleaning import _clean_place
from itinerary_generation.nutshell_model import NutshellLeg
from itinerary_generation.nutshell_parsing import NUTSHELL_ROUTE_PLACES


def _title_endpoints(title: str) -> tuple[str, str]:
    value = str(title or "")
    city = NUTSHELL_ROUTE_PLACES
    full = re.search(
        rf"\bnorway\s+in\s+a\s+(?:nutshell|nuthsell)\s+from\s+(?P<origin>{city})\s+to\s+(?P<destination>{city})\b",
        value,
        flags=re.IGNORECASE,
    )
    if full:
        return _clean_place(full.group("origin")), _clean_place(full.group("destination"))
    destination_only = re.search(
        rf"\bnorway\s+in\s+a\s+(?:nutshell|nuthsell)\s+to\s+(?P<destination>{city})\b",
        value,
        flags=re.IGNORECASE,
    )
    if destination_only:
        return "", _clean_place(destination_only.group("destination"))
    return "", ""


def _direct_route_endpoints(source: str) -> tuple[str, str]:
    city = NUTSHELL_ROUTE_PLACES
    patterns = (
        rf"\|\s*(?P<origin>{city})\s+to\s+(?P<destination>{city})\s*\|",
        rf"^\s*(?P<origin>{city})\s+to\s+(?P<destination>{city})\s*\|\s*Norway\s+in\s+a\s+(?:Nutshell|Nuthsell)",
        rf"\bnorway\s+in\s+a\s+(?:nutshell|nuthsell)\s+(?P<origin>{city})\s+to\s+(?P<destination>{city})\b",
        rf"^\s*(?P<origin>{city})\s+to\s+(?P<destination>{city})(?=\s*[:|\-]|$)",
    )
    for pattern in patterns:
        match = re.search(pattern, source, flags=re.IGNORECASE | re.MULTILINE)
        if not match:
            continue
        origin = _clean_place(match.group("origin"))
        destination = _clean_place(match.group("destination"))
        if origin and destination and origin.lower() != destination.lower():
            return origin, destination
    return "", ""


def _mode_from_supplier_item(item: str) -> str:
    lower = item.lower()
    if "flåm railway" in lower or "flam railway" in lower:
        return "Flåm Railway"
    if "bergen railway" in lower:
        return "Bergen Railway"
    if "voss railway" in lower:
        return "Voss Railway"
    if "fjord cruise" in lower:
        return "Fjord Cruise"
    if "scenic bus" in lower:
        return "Scenic Bus"
    if "coach" in lower:
        return "Coach"
    if "bus" in lower:
        return "Bus"
    if "railway" in lower or "train" in lower or "rail" in lower:
        return "Train"
    if "cruise" in lower:
        return "Cruise"
    return ""


def _supplier_legs(items: Iterable[str]) -> tuple[NutshellLeg, ...]:
    city = NUTSHELL_ROUTE_PLACES
    legs: list[NutshellLeg] = []
    for item in items:
        text = str(item or "").strip()
        match = re.search(
            rf"\b(?P<origin>{city})\s+to\s+(?P<destination>{city})\s*$",
            text,
            flags=re.IGNORECASE,
        )
        if not match:
            continue
        origin = _clean_place(match.group("origin"))
        destination = _clean_place(match.group("destination"))
        if not origin or not destination or origin.lower() == destination.lower():
            continue
        legs.append(
            NutshellLeg(
                origin=origin,
                destination=destination,
                mode=_mode_from_supplier_item(text),
                source_text=text,
            )
        )
    return tuple(legs)


def _mapping_legs(values: Any) -> tuple[NutshellLeg, ...]:
    if not isinstance(values, (list, tuple)):
        return ()
    legs: list[NutshellLeg] = []
    for value in values:
        if not isinstance(value, Mapping):
            continue
        leg = NutshellLeg.from_mapping(value)
        if leg.origin and leg.destination and leg.origin.lower() != leg.destination.lower():
            legs.append(leg)
    return tuple(legs)


def _legs_from_points(points: tuple[str, ...]) -> tuple[NutshellLeg, ...]:
    if len(points) < 2:
        return ()
    return tuple(
        NutshellLeg(origin=points[index], destination=points[index + 1])
        for index in range(len(points) - 1)
        if points[index].lower() != points[index + 1].lower()
    )


def _ordered_points_from_legs(legs: tuple[NutshellLeg, ...]) -> tuple[tuple[str, ...], bool]:
    if not legs:
        return (), True
    points = [legs[0].origin]
    continuous = True
    for leg in legs:
        if points[-1].lower() != leg.origin.lower():
            continuous = False
            break
        points.append(leg.destination)
    return (tuple(points) if continuous else ()), continuous


def _direction(origin: str, destination: str) -> str:
    if not origin or not destination:
        return ""

    def token(value: str) -> str:
        clean = canonicalize_place_name(value).lower()
        clean = clean.replace("å", "a").replace("æ", "ae").replace("ø", "o")
        return re.sub(r"[^a-z0-9]+", "_", clean).strip("_")

    return f"{token(origin)}_to_{token(destination)}"


__all__ = [
    "_direct_route_endpoints",
    "_direction",
    "_legs_from_points",
    "_mapping_legs",
    "_mode_from_supplier_item",
    "_ordered_points_from_legs",
    "_supplier_legs",
    "_title_endpoints",
]

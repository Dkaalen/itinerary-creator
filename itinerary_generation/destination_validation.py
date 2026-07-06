"""Destination validation primitives without transport dependencies."""

from __future__ import annotations

import re

from place_aliases import canonicalize_place_name, is_likely_service_text

_SERVICE_SUFFIX_RE = re.compile(
    r"^\s*(?:private|shared|guided|self[-\s]?guided|optional|transfer|transport|flight|train|cruise|ferry|arrival|departure)\b",
    flags=re.IGNORECASE,
)


def strip_service_suffix(value: str) -> str:
    """Remove parser bleed such as ``Tromsø: Private`` from a city label."""

    text = str(value or "").strip()
    if ":" not in text:
        return text
    left, right = [part.strip() for part in text.split(":", 1)]
    if left and right and _SERVICE_SUFFIX_RE.search(right):
        return left
    return text


def is_valid_destination_city(city) -> bool:
    """Return whether a label is a real destination city, not service text."""

    city = canonicalize_place_name(str(city or "").strip())
    if not city:
        return False
    lower = city.lower()
    invalid_markers = [
        "private hotel",
        "private airport",
        "hotel to airport",
        "airport to hotel",
        "your hotel",
        "your accommodation",
        "your new accommodation",
        "optional addon",
        "optional add",
        "optinal addon",
        "addon on request",
        "flight ",
    ]
    invalid_exact = {
        "accommodation",
        "hotel",
        "train",
        "flight",
        "cruise",
        "departure",
        "arrival",
        "car",
        "drive",
        "self drive",
        "self-drive",
        "the",
        "the airport",
        "airport",
        "the station",
        "station",
        "the hotel",
        "your hotel",
        "the accommodation",
        "your accommodation",
        "shuttle / flybus",
        "shuttle flybus",
        "flybus",
        "city centre",
        "city center",
    }
    if lower in invalid_exact:
        return False
    if any(
        re.search(pattern, lower)
        for pattern in [
            r"\bshower\b",
            r"\bsink\b",
            r"\bwc in carriage\b",
            r"\bbenefits\b",
            r"\bmade bed\b",
            r"women's",
            r"men's compartment",
        ]
    ):
        return False
    if is_likely_service_text(city):
        return False
    if any(marker in lower for marker in invalid_markers):
        return False
    if " to " in lower and any(word in lower for word in ["airport", "hotel", "station", "bergen", "copenhagen", "svol"]):
        return False
    return True

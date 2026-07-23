"""Activity-row detection for rail/fjord transport packages."""

from __future__ import annotations

import re

from itinerary_domain.activity_products import fingerprint_activity
from itinerary_domain.transport_norway import _is_norway_in_a_nutshell_text
from normalizer_modules.text_utils import text_blob


def is_sightseeing_cruise_activity(text: str) -> bool:
    """Return True for cruise wording that is an experience, not route transport."""

    return any(
        marker in str(text or "").lower()
        for marker in [
            "northern lights cruise",
            "fjord cruise day trip",
            "private fjord cruise",
            "fjord cruise |",
            "fjord tour",
            "sightseeing cruise",
            "day cruise",
            "canal cruise",
            "archipelago cruise",
            "wildlife cruise",
            "silent electric ship",
            "cruise on the oslofjord",
            "mostraumen fjord cruise",
            "mostraumen",
            "geirangerfjord",
            "geiranger fjord",
            "trollfjord",
            "nærøyfjord sightseeing cruise",
            "naeroyfjord sightseeing cruise",
            "icebreaker cruise",
            "arctic explorer icebreaker",
            "polar explorer icebreaker",
            "finnish arctic explorer",
            "survival suits",
            "walk on the frozen sea",
            "float in icy arctic waters",
            "cruise & swim certificate",
        ]
    )


def is_rail_or_fjord_route_activity(row: dict) -> bool:
    """Return True when an Activity row is actually route transport."""

    text = text_blob(row).lower()
    source_title = str(row.get("original_title") or row.get("title") or "").lower()
    source_city = str(row.get("city") or "").strip().lower()
    round_trip_markers = ("round-trip", "round trip")
    returns_to_source_city = bool(
        source_city
        and re.search(
            rf"\b(?:return|returns|returning)\s+to\s+{re.escape(source_city)}\b",
            text,
            flags=re.IGNORECASE,
        )
    )
    if any(marker in source_title for marker in round_trip_markers) or returns_to_source_city:
        return False
    product = fingerprint_activity(row)
    if product and product.canonical_family in {"bergen_guided_flam_day_tour"}:
        return False
    if is_sightseeing_cruise_activity(text) and not any(
        marker in text
        for marker in [
            "norway in a nutshell",
            "luggage transfer",
            "flåm railway",
            "flam railway",
            "flåm train",
            "flam train",
            "train transfer",
            "bergen railway",
            "myrdal",
            "voss to",
            "gudvangen to",
        ]
    ):
        return False
    return bool(
        _is_norway_in_a_nutshell_text(text)
        or re.search(r"\btrain\s*[:|]", text)
        or ("flåm train" in text or "flam train" in text or "flåm railway" in text or "flam railway" in text)
        or (
            ("nærøyfjord" in text or "naeroyfjord" in text)
            and ("rail" in text or "train" in text or "luggage transfer" in text)
        )
    )


# Compatibility for older private imports.
_is_sightseeing_cruise_activity = is_sightseeing_cruise_activity
_is_rail_or_fjord_route_activity = is_rail_or_fjord_route_activity


__all__ = [
    "is_sightseeing_cruise_activity",
    "is_rail_or_fjord_route_activity",
    "_is_sightseeing_cruise_activity",
    "_is_rail_or_fjord_route_activity",
]

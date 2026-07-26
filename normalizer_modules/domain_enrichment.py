"""Semantic classification and enrichment for parsed itinerary rows.

Raw parsing extracts source-shaped fields.  This module owns semantic type
classification, source-route hints, source-aware product corrections and input
review metadata before type-specific normalization begins.
"""

from __future__ import annotations

import re

from itinerary_domain.activity_products import fingerprint_activity
from itinerary_domain.row_type_detection import detect_effective_type
from itinerary_generation.transport_domain import get_transport_route_facts
from normalizer_modules.source_row_standardization import standardize_source_row_text
from normalizer_modules.text_utils import text_blob
from normalizer_modules.transport_activity_detection import _is_rail_or_fjord_route_activity
from normalizer_modules.transport_transfer_detection import _is_route_transfer_activity
from itinerary_domain.source_route_parsing import extract_route_points
from itinerary_domain.input_row_quality import confidence_from_review_flags, parser_review_flags

_TRANSPORT_OWNER_TYPES = frozenset(
    {"Transfer", "Transport", "Train", "Flight", "Cruise", "Ferry", "Drive", "Car"}
)


def _attach_source_route_hints(row: dict, detected_type: str) -> None:
    """Preserve source-derived route hints without deciding canonical facts."""

    if detected_type not in _TRANSPORT_OWNER_TYPES:
        return
    route_source = str(row.get("details") or "") or " ".join(
        part for part in (str(row.get("title") or ""), str(row.get("details") or "")) if part
    )
    origin, destination = extract_route_points(route_source)
    if destination and not origin and row.get("city"):
        origin = str(row.get("city") or "")
    if origin and not row.get("route_origin"):
        row["route_origin"] = origin
    if destination and not row.get("route_destination"):
        row["route_destination"] = destination


def _apply_source_owned_activity_classification(row: dict, detected_type: str) -> str:
    """Apply Activity-owned exceptions after generic type detection."""

    if str(row.get("type") or "").strip() != "Activity":
        return detected_type

    full = text_blob(row)
    effective_type = detected_type
    is_accommodation_transfer = bool(
        effective_type == "Transfer"
        and re.search(
            r"\btransfer\s+to\s+(?:glass\s+)?(?:igloo|hotel|accommodation|resort|cabin|lodge)\b|"
            r"\btransfer\s+to\s+[^.]{0,40}stay\b",
            full,
            flags=re.IGNORECASE,
        )
    )
    if effective_type != "Activity" and not (
        _is_rail_or_fjord_route_activity(row)
        or _is_route_transfer_activity(row)
        or is_accommodation_transfer
    ):
        effective_type = "Activity"

    product = fingerprint_activity(row)
    if product and product.product_type == "ferry_excursion":
        effective_type = "Activity"
    return effective_type


def enrich_normalized_row_domain(row: dict) -> str:
    """Enrich one parsed row and return its final semantic type.

    Ordering intentionally mirrors the established full pipeline: generic type
    detection and source-route extraction happen before source-aware Activity
    corrections.  This keeps normalized production output stable while moving
    all semantic decisions out of raw parsing.
    """

    source_type = str(row.get("type") or "").strip()
    detected_type = detect_effective_type(
        source_type,
        str(row.get("title") or ""),
        str(row.get("details") or ""),
    )
    row["effective_type"] = detected_type
    _attach_source_route_hints(row, detected_type)
    standardize_source_row_text(row)
    quality_row = dict(row)
    facts = get_transport_route_facts(row)
    if facts.origin and not quality_row.get("route_origin"):
        quality_row["route_origin"] = facts.origin
    if facts.destination and not quality_row.get("route_destination"):
        quality_row["route_destination"] = facts.destination
    computed_flags = parser_review_flags(quality_row, include_route_checks=True)
    if "parser_review_flags" in row:
        stable_flags = [
            str(flag)
            for flag in row.get("parser_review_flags", [])
            if str(flag) not in {"missing_city", "missing_route_origin", "missing_route_destination"}
        ]
        merged_flags = []
        if "missing_city" in computed_flags:
            merged_flags.append("missing_city")
        merged_flags.extend(flag for flag in stable_flags if flag not in merged_flags)
        merged_flags.extend(
            flag
            for flag in computed_flags
            if flag in {"missing_route_origin", "missing_route_destination"} and flag not in merged_flags
        )
        flags = tuple(merged_flags)
    else:
        flags = computed_flags
    row["parser_review_flags"] = list(flags)
    row["parser_confidence"] = confidence_from_review_flags(flags)

    effective_type = _apply_source_owned_activity_classification(row, detected_type)
    row["effective_type"] = effective_type
    return effective_type


__all__ = ["enrich_normalized_row_domain"]

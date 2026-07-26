"""Effective itinerary row-type detection rules."""
from __future__ import annotations

from shared.row_type_values import normalize_type
from itinerary_domain.row_type_priority import (
    activity_logistics_override,
    direct_mode_override,
    fallback_transport_override,
    preserve_explicit_overview,
    preserve_source_owned_type,
    product_name_override,
    route_mode_override,
    transfer_logistics_override,
)


def _first_override(*values: str | None) -> str | None:
    for value in values:
        if value:
            return value
    return None


def detect_effective_type(item_type, title, details):
    """Return the safest normalized itinerary row type for one source row."""

    combined = f"{title} {details}".lower().strip()
    normalized_item_type = normalize_type(item_type)

    override = _first_override(
        preserve_source_owned_type(normalized_item_type),
        preserve_explicit_overview(normalized_item_type),
        activity_logistics_override(normalized_item_type, combined),
        transfer_logistics_override(normalized_item_type, combined),
        product_name_override(combined),
        route_mode_override(normalized_item_type, combined),
        direct_mode_override(combined),
        fallback_transport_override(normalized_item_type, combined),
    )
    return override or normalized_item_type


__all__ = ["detect_effective_type"]

"""Compatibility facade for Norway in a Nutshell transport parsing."""

from __future__ import annotations

from itinerary_generation.nutshell_parsing import (  # noqa: F401
    NUTSHELL_INTERCHANGE_ONLY_NODES,
    NUTSHELL_ROUTE_PLACES,
    _is_norway_in_a_nutshell_text,
    explicit_norway_nutshell_destination,
    explicit_norway_nutshell_title,
    extract_norway_nutshell_route_legs,
    extract_norway_nutshell_route_points,
    extract_norway_nutshell_supplier_includes,
    format_norway_nutshell_route,
    has_norway_in_a_nutshell,
    is_nutshell_internal_route_node,
    should_preserve_nutshell_origin_label,
)


def _norway_nutshell_route_label(text, fallback_origin="", fallback_destination=""):
    """Compatibility wrapper around the canonical Nutshell domain title."""

    from itinerary_generation.nutshell_domain import build_nutshell_journey

    journey = build_nutshell_journey(
        str(text or ""),
        fallback_origin=fallback_origin,
        fallback_destination=fallback_destination,
    )
    return journey.client_title if journey else "Norway in a Nutshell"

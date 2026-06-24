"""Compatibility labels for Norway in a Nutshell transport parsing."""

from __future__ import annotations


def _norway_nutshell_route_label(text, fallback_origin="", fallback_destination=""):
    """Return the canonical client label without creating a parser/domain cycle."""

    from itinerary_generation.nutshell_domain import build_nutshell_journey

    journey = build_nutshell_journey(
        str(text or ""),
        fallback_origin=fallback_origin,
        fallback_destination=fallback_destination,
    )
    return journey.client_title if journey else "Norway in a Nutshell"

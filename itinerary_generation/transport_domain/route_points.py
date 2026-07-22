"""Cached public route-point access for transport rows."""
from __future__ import annotations

from functools import lru_cache

from itinerary_generation.transport_domain.route_inference import _get_route_points_for_transport_uncached

def _route_row_signature(row) -> tuple[str, ...]:
    if not isinstance(row, dict):
        return (str(row),)
    return (
        str(row.get("row_id") or row.get("line_number") or ""),
        str(row.get("type") or ""),
        str(row.get("effective_type") or ""),
        str(row.get("city") or ""),
        str(row.get("title") or ""),
        str(row.get("original_title") or ""),
        str(row.get("details") or ""),
        str(row.get("raw") or row.get("raw_text") or ""),
        str(row.get("route_origin") or ""),
        str(row.get("route_destination") or ""),
    )


def _row_from_route_signature(signature: tuple[str, ...]) -> dict:
    if len(signature) == 1:
        return {"title": signature[0]}
    (
        row_id,
        row_type,
        effective_type,
        city,
        title,
        original_title,
        details,
        raw,
        route_origin,
        route_destination,
    ) = signature
    return {
        "row_id": row_id,
        "type": row_type,
        "effective_type": effective_type,
        "city": city,
        "title": title,
        "original_title": original_title,
        "details": details,
        "raw": raw,
        "route_origin": route_origin,
        "route_destination": route_destination,
    }


@lru_cache(maxsize=2048)
def _cached_route_points_for_transport(signature: tuple[str, ...]) -> tuple[str, str]:
    return _get_route_points_for_transport_uncached(_row_from_route_signature(signature))


def get_route_points_for_transport(row):
    """Return normalized (origin, destination) for a transport row."""

    return _cached_route_points_for_transport(_route_row_signature(row))

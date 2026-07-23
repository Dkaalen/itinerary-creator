"""Compatibility accessors for authoritative client transport wording."""

from __future__ import annotations

from text_polish import polish_title
from itinerary_generation.common_constants import TRANSPORT_TYPES
from itinerary_generation.row_filters import get_row_type
from itinerary_generation.transport_detection import is_route_transfer
from itinerary_generation.transport_model import get_transport_source_text, has_local_transfer_marker
from itinerary_generation.nutshell_domain import resolve_nutshell_journey
from itinerary_generation.transport_domain.client_wording import build_client_transport_wording
from itinerary_generation.transport_domain.routes import get_route_points_for_transport


def get_transport_route_phrase(row):
    """Return the full factual client phrase for arrangements and inclusions."""

    return build_client_transport_wording(dict(row)).arrangement_title


def get_premium_transport_phrase(row):
    """Backward-compatible alias for the authoritative full route phrase."""

    return get_transport_route_phrase(row)


def get_transfer_travel_title(row):
    """Return the same factual phrase used by every other transport surface."""

    return build_client_transport_wording(dict(row)).arrangement_title


def _destination_focused_transport_title(row, route_phrase: str) -> str:
    """Return the concise day-heading phrase from the shared wording contract."""

    return build_client_transport_wording(dict(row)).day_title or polish_title(route_phrase)


def _multi_leg_transport_day_title(day_rows) -> str:
    transport_rows = [row for row in day_rows if get_row_type(row) in set(TRANSPORT_TYPES) | {"Transport", "Coach", "Bus", "Drive"}]
    if len(transport_rows) < 2:
        return ""

    final_city = ""
    for row in reversed(day_rows):
        if get_row_type(row) == "Hotel" and row.get("city"):
            final_city = polish_title(str(row.get("city") or ""))
            break
    if not final_city:
        for row in reversed(transport_rows):
            _, destination = get_route_points_for_transport(row)
            if destination:
                final_city = polish_title(destination)
                break
    if not final_city:
        return ""

    intermediate_points: list[str] = []
    for row in transport_rows[:-1]:
        _, destination = get_route_points_for_transport(row)
        destination = polish_title(destination)
        if destination and destination.lower() != final_city.lower() and destination not in intermediate_points:
            intermediate_points.append(destination)

    if intermediate_points:
        return f"Journey to {final_city} via {' and '.join(intermediate_points[:2])}"
    return f"Journey to {final_city}"


def get_primary_transport_title(day_rows):
    multi_leg_title = _multi_leg_transport_day_title(day_rows)
    if multi_leg_title:
        return multi_leg_title

    for preferred_type in ["Flight", "Train", "Drive", "Transport", "Cruise", "Ferry"]:
        for row in day_rows:
            if get_row_type(row) == preferred_type:
                source_text = get_transport_source_text(row)
                if preferred_type == "Transport" and has_local_transfer_marker(source_text.lower()):
                    has_main_transport = any(
                        get_row_type(other) == preferred_type
                        and not has_local_transfer_marker(get_transport_source_text(other).lower())
                        for other in day_rows
                    )
                    if has_main_transport:
                        continue
                nutshell_journey = resolve_nutshell_journey(row)
                if nutshell_journey is not None:
                    # Day headings stay destination-focused, while the product
                    # line and inclusions keep the canonical full route title.
                    return (
                        f"Norway in a Nutshell to {nutshell_journey.destination}"
                        if nutshell_journey.destination
                        else nutshell_journey.client_title
                    )
                route_phrase = get_transport_route_phrase(row)
                if route_phrase:
                    return _destination_focused_transport_title(row, route_phrase)
                title = polish_title(str(row.get("title", "")).strip())
                if title:
                    return title

    for row in day_rows:
        if is_route_transfer(row):
            route_phrase = get_transport_route_phrase(row)
            if route_phrase:
                return _destination_focused_transport_title(row, route_phrase)
            return get_transfer_travel_title(row)

    return ""


def get_first_transfer_title(day_rows):
    for row in day_rows:
        if get_row_type(row) == "Transfer":
            title = str(row.get("title", "")).strip()
            if title:
                return title
    return ""

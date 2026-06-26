"""Canonical client-facing transport labels and titles."""

from __future__ import annotations

import re

from place_aliases import canonicalize_place_name
from text_polish import polish_title
from itinerary_generation.common import TRANSPORT_TYPES, get_row_type
from itinerary_generation.transport_detection import is_route_transfer
from itinerary_generation.transport_model import get_transport_source_text, has_local_transfer_marker
from itinerary_generation.nutshell_domain import resolve_nutshell_journey
from itinerary_generation.transport_safety import base_destination_from_terminal
from itinerary_generation.transport_domain.routes import (
    _clean_route_place,
    _via_suffix,
    get_route_points_for_transport,
    get_route_via_points,
    _route_destination_from_text,
)


def get_transport_route_phrase(row):
    """Client-facing transport label for day arrangements and inclusions."""
    row_type = get_row_type(row)
    text = get_transport_source_text(row)
    lower = text.lower()
    nutshell_journey = resolve_nutshell_journey(row)
    if nutshell_journey is not None:
        return nutshell_journey.client_title

    origin, destination = get_route_points_for_transport(row)
    via = get_route_via_points(row, origin, destination)

    if row_type == "Transfer" and has_local_transfer_marker(lower) and not is_route_transfer(row):
        return polish_title(row.get("title", "") or "Transfer")

    if row_type == "Train" or "train" in lower:
        if "santa claus express" in lower:
            label = "Santa Claus Express"
        elif re.search(r"\b(?:overnight|night\s+train|sleeper|sleeping)\b", lower):
            label = "Overnight Train Transfer"
        elif re.search(r"\bday\s+train\b|\bintercity\s*\d+\b", lower):
            label = "Train"
        else:
            label = "Scenic Train Transfer"
        if label == "Santa Claus Express":
            santa_destination = re.search(r"\bsanta\s+claus\s+express\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)(?:\s+-\s+\d{1,2}:\d{2}|\s+-\s+Arrival|\s+\|\s+|\s+-\s+|$)", text, flags=re.IGNORECASE)
            if santa_destination:
                destination = _clean_route_place(santa_destination.group(1))
                origin = ""
                via = []
        if origin and destination:
            return f"{label} from {origin} to {destination}{_via_suffix(via)}"
        if destination:
            return f"{label} to {destination}"
        title_destination_match = re.search(r"\btrain\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ ]+)", str(row.get("title", "") or ""), flags=re.IGNORECASE)
        if title_destination_match:
            title_dest = _clean_route_place(title_destination_match.group(1))
            if title_dest:
                return f"{label} to {title_dest}"
        city_destination = _clean_route_place(row.get("city", ""))
        if city_destination and city_destination.lower() not in {"station", "airport", "accommodation"}:
            return f"{label} to {city_destination}"
        return label

    if row_type == "Flight" or "flight" in lower:
        if origin and destination:
            return f"Flight from {origin} to {destination}{_via_suffix(via)}"
        if destination:
            return f"Flight to {destination}"
        return "Flight"

    if (row_type == "Transport" and re.search(r"\b(coach|bus)\b", lower)) or (row_type == "Transfer" and re.search(r"\b(coach|bus)\b", lower)):
        if "panorama" in lower or "panoramic" in lower or "scenic" in lower:
            label = "Panoramic Coach Transfer"
        elif "long distance" in lower or "long-distance" in lower:
            label = "Long-distance Coach Transfer"
        else:
            label = "Coach Transfer"
        if origin and destination:
            return f"{label} from {origin} to {destination}"
        if destination:
            return f"{label} to {destination}"
        return label

    if row_type in {"Cruise", "Ferry"} or "cruise" in lower or "ferry" in lower:
        if "geiranger fjord cruise" in lower or "geirangerfjord" in lower:
            if destination and destination.lower() == "geiranger":
                return "Geirangerfjord Cruise from Ålesund to Geiranger" if origin else "One-way Geirangerfjord Cruise to Geiranger"
        is_ferry = row_type == "Ferry" or ("ferry" in lower and "cruise" not in lower)
        if row_type == "Cruise" and "arrival" in lower and "overnight" not in lower:
            return f"Cruise arrival to {destination}" if destination else "Cruise arrival"
        if is_ferry:
            label = "Ferry Transfer"
            if origin and destination:
                return f"{label} from {origin} to {destination}"
            if destination:
                return f"{label} to {destination}"
            return label
        label = "Overnight Coastal Cruise" if "overnight" in lower else ("Nærøyfjord Cruise" if "nærøyfjord" in lower or "naeroyfjord" in lower else "Coastal Cruise")
        if origin and destination:
            phrase = f"{label} from {origin} to {destination}"
        elif destination:
            phrase = f"{label} to {destination}"
        else:
            phrase = label
        ship_match = re.search(r"\bonboard\s+([^|,;]+?)(?:\s+-\s+|\s+\||,|;|$)", text, flags=re.IGNORECASE)
        if ship_match:
            ship = polish_title(ship_match.group(1).strip(" .-:|"))
            if ship and ship.lower() not in phrase.lower():
                phrase += f" onboard {ship}"
        return phrase

    if row_type == "Transfer" and is_route_transfer(row):
        return get_transfer_travel_title(row)

    return polish_title(row.get("title", "") or "Travel")


def get_premium_transport_phrase(row):
    """Backward-compatible alias for older imports.

    New code should use get_transport_route_phrase(), which better matches
    the app's down-to-earth wording direction.
    """

    return get_transport_route_phrase(row)

def get_transfer_travel_title(row):
    text = f'{row.get("title", "")} {row.get("details", "")}'
    lower = text.lower()
    route_origin, route_destination = get_route_points_for_transport(row)
    text_destination = _route_destination_from_text(text)
    city_destination = canonicalize_place_name(row.get("city", ""))

    if "flight" in lower:
        destination = text_destination or route_destination or city_destination
        return f"Flight to {destination}" if destination else polish_title(row.get("title", "") or "Flight")
    if "train" in lower:
        destination = text_destination or route_destination or city_destination
        return f"Train to {destination}" if destination else polish_title(row.get("title", "") or "Train")
    if "ferry" in lower or "cruise" in lower:
        destination = text_destination or route_destination or city_destination
        if destination:
            return f"Ferry to {destination}" if "ferry" in lower else f"Cruise to {destination}"
    if "coach" in lower or "bus" in lower:
        destination = base_destination_from_terminal(route_destination or text_destination or city_destination)
        return f"Coach Transfer to {destination}" if destination else polish_title(row.get("title", "") or "Coach Transfer")
    if ("shuttle" in lower or "transfer" in lower) and route_origin and route_destination:
        label = "Shuttle transfer" if "shuttle" in lower else "Transfer"
        return f"{label} from {route_origin} to {route_destination}"

    destination = text_destination or route_destination or city_destination
    if destination:
        return f"Travel to {destination}"
    return polish_title(row.get("title", "") or "Travel today")


def _destination_focused_transport_title(row, route_phrase: str) -> str:
    """Return a concise day-heading version of a route transport phrase.

    Detailed route wording belongs in the travel-arrangements block and final
    inclusions. Day headings should usually communicate the movement and final
    destination without operational clutter such as origin stations, tickets or
    timing.
    """

    _, destination = get_route_points_for_transport(row)
    if not destination:
        return polish_title(route_phrase)

    lower = f"{route_phrase} {get_transport_source_text(row)}".lower()
    destination = polish_title(base_destination_from_terminal(destination) or destination)
    if "flight" in lower:
        return f"Flight to {destination}"
    if "train" in lower:
        if "santa claus express" in lower:
            return f"Santa Claus Express to {destination}"
        return f"Overnight train to {destination}" if re.search(r"\b(?:overnight|night\s+train|sleeper|sleeping)\b", lower) else f"Train to {destination}"
    if "coach" in lower or "bus" in lower:
        return f"Coach Transfer to {destination}"
    if "shuttle" in lower or "transfer" in lower:
        return f"Transfer to {destination}"
    if "ferry" in lower:
        return f"Ferry to {destination}"
    if "cruise" in lower:
        return f"Cruise arrival to {destination}" if "arrival" in lower else f"Cruise to {destination}"
    return polish_title(route_phrase)


def _multi_leg_transport_day_title(day_rows) -> str:
    transport_rows = [row for row in day_rows if get_row_type(row) in set(TRANSPORT_TYPES) | {"Transport", "Coach", "Bus"}]
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

    for preferred_type in ["Flight", "Train", "Transport", "Cruise", "Ferry"]:
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

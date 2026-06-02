"""Client-facing labels and titles for transport rows."""

from __future__ import annotations

import re

from place_aliases import canonicalize_place_name
from text_polish import polish_title
from itinerary_generation.common import get_row_type
from itinerary_generation.transport_detection import is_route_transfer
from itinerary_generation.transport_model import get_transport_source_text, has_local_transfer_marker
from itinerary_generation.transport_norway import _is_norway_in_a_nutshell_text, _norway_nutshell_route_label
from itinerary_generation.transport_routes import (
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
    origin, destination = get_route_points_for_transport(row)
    via = get_route_via_points(row, origin, destination)

    if row_type == "Transfer" and has_local_transfer_marker(lower):
        return polish_title(row.get("title", "") or "Transfer")

    if row_type == "Train" or "train" in lower:
        if _is_norway_in_a_nutshell_text(text):
            return _norway_nutshell_route_label(text, origin, destination)
        label = "Overnight Train Transfer" if re.search(r"\b(?:overnight|night\s+train|sleeper|sleeping)\b", lower) else "Scenic Train Transfer"
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
        if row_type == "Cruise" and "arrival" in lower:
            return f"Cruise arrival to {destination}" if destination else "Cruise arrival"
        if is_ferry:
            label = "Ferry Transfer"
            if origin and destination:
                return f"{label} from {origin} to {destination}"
            if destination:
                return f"{label} to {destination}"
            return label
        label = "Overnight Coastal Cruise" if "overnight" in lower else "Coastal Cruise"
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
    _, route_destination = get_route_points_for_transport(row)
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
        destination = route_destination or text_destination or city_destination
        return f"Coach Transfer to {destination}" if destination else polish_title(row.get("title", "") or "Coach Transfer")

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
    destination = polish_title(destination)
    if "flight" in lower:
        return f"Flight to {destination}"
    if "train" in lower:
        return f"Overnight train to {destination}" if re.search(r"\b(?:overnight|night\s+train|sleeper|sleeping)\b", lower) else f"Train to {destination}"
    if "coach" in lower or "bus" in lower:
        return f"Coach Transfer to {destination}"
    if "ferry" in lower:
        return f"Ferry to {destination}"
    if "cruise" in lower:
        return f"Cruise arrival to {destination}" if "arrival" in lower else f"Cruise to {destination}"
    return polish_title(route_phrase)


def get_primary_transport_title(day_rows):
    for preferred_type in ["Flight", "Train", "Transport", "Cruise", "Ferry"]:
        for row in day_rows:
            if get_row_type(row) == preferred_type:
                source_text = get_transport_source_text(row)
                if _is_norway_in_a_nutshell_text(source_text):
                    route_phrase = get_transport_route_phrase(row)
                    if route_phrase:
                        # Day titles read cleaner with destination focus, while
                        # inclusions/travel lines keep the full from/to route.
                        dest_match = re.search(r"\bto\s+([A-Za-zÀ-ÿøØåÅäÄöÖ]+)\s*$", route_phrase)
                        return f"Norway in a Nutshell to {polish_title(dest_match.group(1))}" if dest_match else route_phrase
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

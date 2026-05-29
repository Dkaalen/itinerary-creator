"""Client-facing labels and titles for transport rows."""

from __future__ import annotations

import re

from place_aliases import canonicalize_place_name
from text_polish import polish_title
from itinerary_generation.common import get_row_type
from itinerary_generation.transport_detection import is_route_transfer
from itinerary_generation.transport_norway import _is_norway_in_a_nutshell_text, _norway_nutshell_route_label
from itinerary_generation.transport_routes import (
    _clean_route_place,
    _transport_source_text,
    _via_suffix,
    get_route_points_for_transport,
    get_route_via_points,
    _route_destination_from_text,
)


def get_premium_transport_phrase(row):
    """Client-facing transport label for day arrangements and inclusions."""
    row_type = get_row_type(row)
    text = _transport_source_text(row)
    lower = text.lower()
    origin, destination = get_route_points_for_transport(row)
    via = get_route_via_points(row, origin, destination)

    if row_type == "Transfer" and any(marker in lower for marker in ["private", "self transfer", "shuttle", "hotel to", "airport to", "to hotel", "to airport", "to station", "to your accommodation"]):
        return polish_title(row.get("title", "") or "Transfer")

    if row_type == "Train" or "train" in lower:
        if _is_norway_in_a_nutshell_text(text):
            return _norway_nutshell_route_label(text, origin, destination)
        label = "Overnight Train Transfer" if "overnight" in lower else "Scenic Train Transfer"
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


def get_transfer_travel_title(row):
    text = f'{row.get("title", "")} {row.get("details", "")}'
    lower = text.lower()
    destination = _route_destination_from_text(text) or canonicalize_place_name(row.get("city", ""))

    if "flight" in lower and destination:
        return f"Flight to {destination}"
    if "train" in lower and destination:
        return f"Train to {destination}"
    if ("ferry" in lower or "cruise" in lower) and destination:
        return f"Ferry to {destination}" if "ferry" in lower else f"Cruise to {destination}"
    if ("coach" in lower or "bus" in lower) and destination:
        return f"Coach Transfer to {destination}"
    if destination:
        return f"Travel to {destination}"
    return polish_title(row.get("title", "") or "Travel today")


def get_primary_transport_title(day_rows):
    for preferred_type in ["Flight", "Train", "Transport", "Cruise", "Ferry"]:
        for row in day_rows:
            if get_row_type(row) == preferred_type:
                source_text = _transport_source_text(row)
                if _is_norway_in_a_nutshell_text(source_text):
                    premium = get_premium_transport_phrase(row)
                    if premium:
                        # Day titles read cleaner with destination focus, while
                        # inclusions/travel lines keep the full from/to route.
                        dest_match = re.search(r"\bto\s+([A-Za-zÀ-ÿøØåÅäÄöÖ]+)\s*$", premium)
                        return f"Norway in a Nutshell to {polish_title(dest_match.group(1))}" if dest_match else premium
                title = polish_title(str(row.get("title", "")).strip())
                if title:
                    return title

    for row in day_rows:
        if is_route_transfer(row):
            return get_transfer_travel_title(row)

    return ""


def get_first_transfer_title(day_rows):
    for row in day_rows:
        if get_row_type(row) == "Transfer":
            title = str(row.get("title", "")).strip()
            if title:
                return title
    return ""

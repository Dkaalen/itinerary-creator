"""Parser transport title standardization helpers."""

import re

from .place_parsing import city_airport, extract_route_points, normalize_place_name
from .text_cleanup import fix_common_text
from itinerary_generation.transport_safety import (
    base_destination_from_terminal,
    normalize_transport_place,
    split_self_transfer_notes,
)


def _explicit_airport_from_text(text, fallback_city=""):
    source = text or ""
    directional = re.search(r"\b(?:to|from)\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?\s+Airport)\b", source, flags=re.IGNORECASE)
    if directional:
        airport = normalize_transport_place(directional.group(1))
        if airport:
            return airport
    matches = re.findall(r"\b([A-ZÅÄÖÆØ][A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{1,40}?\s+Airport)\b", source)
    if matches:
        airport = normalize_transport_place(matches[-1])
        if airport:
            return airport
    return city_airport(fallback_city)


def standardize_private_transfer_title(title, details, city):
    text = fix_common_text(details or title)
    lower = text.lower()
    airport = _explicit_airport_from_text(text, city)

    if re.search(r"\bhotel\s+to\s+[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?\s+Airport\b", text, flags=re.IGNORECASE):
        return f"Private transfer from your hotel to {airport}"
    if re.search(r"\b[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?\s+Airport\s+to\s+hotel\b", text, flags=re.IGNORECASE):
        return f"Private transfer from {airport} to your accommodation"

    if "hotel to airport" in lower or "accommodation to airport" in lower:
        return f"Private transfer from your hotel to {airport}"

    if "airport to hotel" in lower or "airport to accommodation" in lower:
        return f"Private transfer from {airport} to your accommodation"

    if "bus station" in lower or "bustation" in lower:
        if "hotel to" in lower or "to bus" in lower:
            return f"Private transfer from your hotel to {normalize_transport_place((city + ' Bus Station').strip()) if city else 'the bus station'}"
        if "to hotel" in lower or "to accommodation" in lower or "station to" in lower:
            return f"Private transfer from {normalize_transport_place((city + ' Bus Station').strip()) if city else 'the bus station'} to your accommodation"

    if "hotel to station" in lower or "accommodation to station" in lower:
        return f"Private transfer from your hotel to {normalize_transport_place((city + ' Railway Station').strip()) if city else 'the railway station'}"

    if "station to hotel" in lower or "station to accommodation" in lower:
        return f"Private transfer from {normalize_transport_place((city + ' Railway Station').strip()) if city else 'the railway station'} to your accommodation"

    if "airport" in lower and "hotel" not in lower and "accommodation" not in lower:
        if " to airport" in lower:
            return f"Private transfer to {airport}"
        if "airport to" in lower:
            return f"Private transfer from {airport}"

    if "to hotel" in lower or "to accommodation" in lower or "to your accommodation" in lower:
        return "Private transfer to your accommodation"

    return fix_common_text(title)


def standardize_self_transfer_title(title, details, city):
    text = fix_common_text(details or title)
    lower = text.lower()
    airport = _explicit_airport_from_text(text, city)

    if "hotel to airport" in lower or "accommodation to airport" in lower or "to airport" in lower:
        return f"Self-arranged transfer from your hotel to {airport}"

    if "airport to hotel" in lower or "airport to accommodation" in lower:
        return f"Self-arranged transfer from {airport} to your accommodation"

    if "bus station" in lower or "bustation" in lower:
        if "hotel to" in lower or "to bus" in lower:
            return f"Self-arranged transfer from your hotel to {normalize_transport_place((city + ' Bus Station').strip()) if city else 'the bus station'}"
        if "to hotel" in lower or "to accommodation" in lower or "station to" in lower:
            return f"Self-arranged transfer from {normalize_transport_place((city + ' Bus Station').strip()) if city else 'the bus station'} to your accommodation"

    if "hotel to station" in lower or "to station" in lower:
        return f"Self-arranged transfer from your hotel to {normalize_transport_place((city + ' Railway Station').strip()) if city else 'the railway station'}"

    if "station to hotel" in lower or "station to accommodation" in lower:
        return f"Self-arranged transfer from {normalize_transport_place((city + ' Railway Station').strip()) if city else 'the railway station'} to your accommodation"

    notes = split_self_transfer_notes(text)
    return notes[0] if notes else fix_common_text(title).replace("Self-guided transfer", "Self transfer")


def standardize_shuttle_transfer_title(title, details, city):
    text = fix_common_text(f"{title} {details}")
    origin, destination = extract_route_points(text)

    if destination:
        if origin:
            return f"Shuttle transfer from {origin} to {destination}"
        return f"Shuttle transfer to {destination}"

    airport = city_airport(city)
    lower = text.lower()

    if "airport" in lower:
        return f"Shuttle transfer to {airport}"

    return fix_common_text(title) or "Shuttle transfer"


def create_clean_transport_title(row):
    row_type = row.get("effective_type") or row.get("type", "")
    title = fix_common_text(row.get("title", ""))
    details = fix_common_text(row.get("details", ""))
    text = f"{title} {details}"
    lower = text.lower()
    origin, destination = extract_route_points(details)
    if not destination:
        origin, destination = extract_route_points(title)
    if not destination:
        origin, destination = extract_route_points(text)
    city = normalize_place_name(row.get("city", ""))

    if "norway in a nutshell" in lower:
        explicit_destination_match = re.search(
            r"\bnorway\s+in\s+a\s+nutshell\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ ]+?)(?:\s+norway\s+in\s+a\s+nutshell|\s+-\s+|\s+\|\s+|$)",
            text,
            flags=re.IGNORECASE,
        )
        if explicit_destination_match:
            return f"Norway in a Nutshell to {normalize_place_name(explicit_destination_match.group(1).strip())}"
        if destination:
            return f"Norway in a Nutshell to {destination}"
        return "Norway in a Nutshell"

    if row_type == "Flight" or "flight" in lower:
        if destination:
            return f"Flight to {destination}"
        if city:
            return f"Flight to {city}"
        return "Flight"

    if row_type == "Train" or "train" in lower:
        prefix = "Santa Claus Express" if "santa claus express" in lower else ("Overnight Train" if "overnight" in lower else "Train")
        if prefix == "Santa Claus Express":
            santa_destination = re.search(r"\bsanta\s+claus\s+express\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)(?:\s+-\s+\d{1,2}:\d{2}|\s+-\s+Arrival|\s+\|\s+|\s+-\s+|$)", text, flags=re.IGNORECASE)
            if santa_destination:
                destination = normalize_place_name(santa_destination.group(1).strip(" -:|.,"))
        if destination:
            return f"{prefix} to {destination}"
        if city:
            return f"{prefix} to {city}"
        return prefix

    if "coach" in lower or "bus" in lower:
        destination = base_destination_from_terminal(destination)
        if destination:
            return f"Coach Transfer to {destination}"
        if city:
            return f"Coach Transfer to {city}"
        return "Coach Transfer"

    if row_type in {"Cruise", "Ferry"}:
        label = "Ferry" if row_type == "Ferry" else "Cruise"
        if row_type == "Cruise" and "spend time at leisure" in lower:
            return "Spend time at leisure onboard the cruise"
        if row_type == "Cruise" and ("onboard" in lower or "on board" in lower) and "leisure" in lower:
            return "Spend time at leisure onboard the cruise"
        cruise_arrival = re.search(r"\barrival\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ\s]+?)(?:\s+at\b|\s*(?:\||-|,|;|$))", text, flags=re.IGNORECASE)
        if row_type == "Cruise" and cruise_arrival:
            arrival_city = normalize_place_name(cruise_arrival.group(1).strip(" -:|."))
            if arrival_city:
                return f"Cruise arrival to {arrival_city}"
        if destination:
            return f"{label} to {destination}"
        if city and city.lower() != "cruise":
            return f"{label} to {city}"
        return label

    return title

"""Parser transport title standardization helpers."""

import re

from .place_parsing import city_airport, extract_route_points, normalize_place_name
from .text_cleanup import fix_common_text


def standardize_private_transfer_title(title, details, city):
    text = fix_common_text(f"{title} {details}")
    lower = text.lower()
    airport = city_airport(city)

    if "hotel to airport" in lower or "accommodation to airport" in lower:
        return f"Private transfer from your hotel to {airport}"

    if "airport to hotel" in lower or "airport to accommodation" in lower:
        return f"Private transfer from {airport} to your accommodation"

    if "bus station" in lower or "bustation" in lower:
        if "hotel to" in lower or "to bus" in lower:
            return "Private transfer from your hotel to the bus station"
        if "to hotel" in lower or "to accommodation" in lower or "station to" in lower:
            return "Private transfer from the bus station to your accommodation"

    if "hotel to station" in lower or "accommodation to station" in lower:
        return "Private transfer from your hotel to the station"

    if "station to hotel" in lower or "station to accommodation" in lower:
        return "Private transfer from the station to your accommodation"

    if "airport" in lower and "hotel" not in lower and "accommodation" not in lower:
        if " to airport" in lower:
            return f"Private transfer to {airport}"
        if "airport to" in lower:
            return f"Private transfer from {airport}"

    if "to hotel" in lower or "to accommodation" in lower or "to your accommodation" in lower:
        return "Private transfer to your accommodation"

    return fix_common_text(title)


def standardize_self_transfer_title(title, details, city):
    text = fix_common_text(f"{title} {details}")
    lower = text.lower()
    airport = city_airport(city)

    if "hotel to airport" in lower or "accommodation to airport" in lower or "to airport" in lower:
        return f"Self transfer from your hotel to {airport}"

    if "airport to hotel" in lower or "airport to accommodation" in lower:
        return f"Self transfer from {airport} to your accommodation"

    if "bus station" in lower or "bustation" in lower:
        if "hotel to" in lower or "to bus" in lower:
            return "Self transfer from your hotel to the bus station"
        if "to hotel" in lower or "to accommodation" in lower or "station to" in lower:
            return "Self transfer from the bus station to your accommodation"

    if "hotel to station" in lower or "to station" in lower:
        return "Self transfer from your hotel to the station"

    if "station to hotel" in lower or "station to accommodation" in lower:
        return "Self transfer from the station to your accommodation"

    return fix_common_text(title).replace("Self-guided transfer", "Self transfer")


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
        prefix = "Overnight Train" if "overnight" in lower else "Train"
        if destination:
            return f"{prefix} to {destination}"
        if city:
            return f"{prefix} to {city}"
        return prefix

    if "coach" in lower or "bus" in lower:
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

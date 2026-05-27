import re

from place_aliases import canonicalize_place_name
from text_polish import polish_client_text, polish_title

from itinerary_generation.common import (
    TRANSPORT_TYPES,
    get_row_type,
    is_self_arranged,
    is_valid_destination_city,
)


def has_airport_arrival_transfer(day_rows):
    text = " ".join(f'{row.get("title", "")} {row.get("details", "")}' for row in day_rows).lower()
    return ("airport" in text and ("to hotel" in text or "to accommodation" in text or "to your accommodation" in text))


def has_airport_departure_transfer(day_rows):
    text = " ".join(f'{row.get("title", "")} {row.get("details", "")}' for row in day_rows).lower()
    return ("airport" in text and ("hotel to" in text or "accommodation to" in text or "to airport" in text))


def _route_destination_from_text(value):
    text = polish_client_text(value)
    if not text or " to " not in text.lower():
        return ""

    # Prefer explicit transport route wording before broad "A to B" matching.
    explicit = re.search(
        r"\b(?:flight|train|coach|bus|ferry|cruise)\s*(?:[:|])?\s*([A-Za-zÀ-ÿøØåÅäÄöÖ\s]+?)\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ\s]+?)(?:\s*(?:\||-|,|;|$)|\s+Day\b|\s+self\b|\s+cost\b|\s+not\b|\s+sitting\b)",
        text,
        flags=re.IGNORECASE,
    )
    if explicit:
        return canonicalize_place_name(re.split(r"\s+(?:train|flight|coach|bus|ferry|cruise)\b|\s+to\s+", explicit.group(2).strip(" -:|."), maxsplit=1, flags=re.IGNORECASE)[0].strip(" -:|."))

    # Use the last route-like destination in the string. This works for messy
    # rows such as "Tromsø to Bergen" or "Flight Bergen to Svolvær".
    matches = list(re.finditer(r"\bfrom\s+(.+?)\s+to\s+([^|,.;\n]+)|\b([^|,.;\n]+?)\s+to\s+([^|,.;\n]+)", text, flags=re.IGNORECASE))
    if not matches:
        return ""

    match = matches[-1]
    destination = match.group(2) or match.group(4) or ""
    destination = destination.strip(" -:|.")
    # Remove trailing supplier/status text.
    destination = re.split(r"\s+(?:self|cost|price|not|included|arranged|day|sitting|seat|train|flight)\b", destination, flags=re.IGNORECASE)[0].strip(" -:|.")
    return canonicalize_place_name(destination)


def is_route_transfer(row):
    if get_row_type(row) != "Transfer":
        return False
    text = f'{row.get("title", "")} {row.get("details", "")}'
    lower = text.lower()
    if any(marker in lower for marker in ["private", "shuttle", "self transfer", "hotel to", "airport to", "station to", "to hotel", "to airport", "to station", "accommodation"]):
        return False
    destination = _route_destination_from_text(text)
    return bool(destination and is_valid_destination_city(destination))


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
        return f"Coach transfer to {destination}"
    if destination:
        return f"Travel to {destination}"
    return polish_title(row.get("title", "") or "Travel today")


def get_primary_transport_title(day_rows):
    for preferred_type in ["Flight", "Train", "Transport", "Cruise", "Ferry"]:
        for row in day_rows:
            if get_row_type(row) == preferred_type:
                title = polish_title(str(row.get("title", "")).strip())
                if title:
                    return title

    for row in day_rows:
        if is_route_transfer(row):
            return get_transfer_travel_title(row)

    return ""


def has_only_departure_arrangements(day_rows):
    """True when a day is essentially only final airport/departure logistics."""
    if not day_rows:
        return False

    allowed_types = {"Transfer", "Departure"}
    row_types = {get_row_type(row) for row in day_rows}

    if not row_types.issubset(allowed_types):
        return False

    return has_airport_departure_transfer(day_rows) or any(get_row_type(row) == "Departure" for row in day_rows)


def get_first_transfer_title(day_rows):
    for row in day_rows:
        if get_row_type(row) == "Transfer":
            title = str(row.get("title", "")).strip()
            if title:
                return title
    return ""


def has_self_arranged_transport(day_rows):
    return any(get_row_type(row) in TRANSPORT_TYPES and is_self_arranged(row) for row in day_rows)


def has_norway_in_a_nutshell(rows):
    text = " ".join(f'{row.get("title", "")} {row.get("details", "")}' for row in rows).lower()
    return "norway in a nutshell" in text


def has_glass_igloo_or_arctic_resort(rows):
    hotel_text = " ".join(
        f'{row.get("hotel_name", "")} {row.get("room_category", "")} {row.get("details", "")}'
        for row in rows
        if get_row_type(row) == "Hotel"
    ).lower()
    return any(marker in hotel_text for marker in ["glass igloo", "kakslauttanen", "arctic resort"])

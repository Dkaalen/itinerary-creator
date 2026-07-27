"""Canonical parser-facing transport title standardization helpers."""

import re

from itinerary_domain.source_place_values import city_airport, normalize_place_name
from itinerary_domain.source_route_parsing import extract_route_points
from shared.source_text_cleanup import fix_common_text
from itinerary_generation.transport_norway import _norway_nutshell_route_label, explicit_norway_nutshell_title
from itinerary_generation.transport_safety import (
    base_destination_from_terminal,
    normalize_transport_place,
    split_self_transfer_notes,
)


def _explicit_transport_route_from_text(text: str):
    place = r"[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?"
    known_places = r"(?:Copenhagen|København|Gothenburg|Göteborg|Oslo|Stockholm|Helsinki|Tallinn|Tallin|Bergen|Reykjavík|Reykjavik|Rovaniemi|Tromsø|Tromso|Alta|Gudvangen|Voss|Flåm|Flam|Myrdal)"
    patterns = [
        rf"\b(?:day\s+)?(?:train|flight|coach|bus|cruise|ferry)\s*[:,]?\s*(?P<origin>{known_places})\s*[-–—]\s*(?P<destination>{known_places})(?=\s*(?:\n|intercity\b|ic\b|train\b|flight\b|coach\b|bus\b|cruise\b|ferry\b|\d{{1,2}}:\d{{2}}|$))",
        rf"\b(?:(?:overnight|night)\s+)?(?:cruise|ferry|train|flight|coach|bus)\s*[:,]?\s*(?P<origin>{place})\s+to\s+(?P<destination>{place})(?:\s*\||\s+-\s+|\s+\d{{1,2}}(?::|\s|$)|\s+self[-\s]*arranged|\s+self\s+arranged|\s+cost\s+not|\s*,?\s*tickets?\s+to\s+be\s+bought|\s*,?\s*tickets?\s+to\s+be\s+purchased|,|$)",
        rf"\b(?P<origin>{place})\s+to\s+(?P<destination>{place})\s+(?:\d+\s*(?:hr|hrs|hour|hours)\s+)?(?:cruise|ferry|train|flight|coach|bus)\b",
        rf"\b(?P<origin>{place})\s+to\s+(?P<destination>{place})\s*\|",
        rf"\b(?:train|flight|coach|bus|cruise|ferry)\s+(?P<origin>{known_places})\s+(?P<destination>{known_places})\b",
        rf"\b(?P<origin>{known_places})\s+to\s+(?P<destination>{known_places})\s+(?:train|flight|coach|bus|cruise|ferry)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, str(text or ""), flags=re.IGNORECASE)
        if not match:
            continue
        raw_origin = match.group("origin").strip(" -:|.,")
        raw_origin = re.sub(
            r"^(?:long[-\s]*distance\s+comfortable\s+panorama\s+coach\s+transfer|long[-\s]*distance\s+panorama\s+coach\s+transfer|panoramic\s+coach\s+transfer|panorama\s+coach\s+transfer|coach\s+transfer|bus\s+transfer|transfer)\s+from\s+",
            "",
            raw_origin,
            flags=re.IGNORECASE,
        ).strip(" -:|.,")
        origin = normalize_place_name(raw_origin)
        destination = normalize_place_name(match.group("destination").strip(" -:|.,"))
        if origin and destination and origin.lower() != destination.lower():
            return origin, destination
    return "", ""


def _compact_route_destination(destination: str, fallback_city: str = "") -> str:
    """Return a client-safe destination label for transport titles."""

    cleaned = normalize_transport_place(destination) or fix_common_text(destination).strip(" -:|,.")
    cleaned = re.split(
        r"\s+(?:booking window|final timing|timing can vary|tickets? included|incl\.?|includes?|booked seats)\b",
        cleaned,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" -:|,.")
    cleaned = re.sub(r"^(?:from|to)\s+", "", cleaned, flags=re.IGNORECASE).strip(" -:|,.")
    if ":" in cleaned:
        before_colon = cleaned.split(":", 1)[0].strip(" -:|,.")
        normalized_before = normalize_transport_place(before_colon)
        if normalized_before:
            cleaned = normalized_before
    if (
        not cleaned
        or len(cleaned) > 55
        or re.search(r"\b(?:direct|high[-\s]*speed|booked seats|timing can vary|tickets? included|incl\.?|booking window|voucher)\b", cleaned, flags=re.IGNORECASE)
    ):
        return fallback_city
    return cleaned


def _explicit_airport_from_text(text, fallback_city=""):
    source = text or ""
    directional = re.search(r"\b(?:to|from)\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?\s+Airport)\b", source, flags=re.IGNORECASE)
    if directional:
        raw_airport = directional.group(1).strip()
        if raw_airport.lower() not in {"private airport", "airport", "the airport"}:
            airport = normalize_transport_place(raw_airport)
            if airport:
                return airport
    matches = re.findall(r"\b([A-ZÅÄÖÆØ][A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{1,40}?\s+Airport)\b", source)
    for raw_airport in reversed(matches):
        if raw_airport.strip().lower() in {"private airport", "airport", "the airport"}:
            continue
        airport = normalize_transport_place(raw_airport)
        if airport:
            return airport
    return city_airport(fallback_city)




def _clean_route_endpoint(value: str) -> str:
    endpoint = fix_common_text(value).strip(" -:|,.")
    endpoint = re.split(
        r",\s*(?:[A-ZÀ-Ýa-zà-ÿ .'-]*(?:gate|gade|gata|street|road|avenue|vei|veien|tollbodgate)\b|\d)",
        endpoint,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" -:|,.")
    return normalize_transport_place(endpoint) or endpoint


def _generic_private_transfer_route_title(text: str) -> str:
    match = re.search(
        r"\bprivate\s+transfer\s+(?:from\s+)?(?P<origin>.+?)\s+to\s+(?P<destination>.+?)(?:\s*\||\s+-\s+|,\s*(?:tickets?|price|cost|incl\.?|includes?|[A-ZÀ-Ýa-zà-ÿ .'-]*(?:gate|gade|gata|street|road|avenue|vei|veien|tollbodgate)\b|\d)|$)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    origin = _clean_route_endpoint(match.group("origin"))
    destination = _clean_route_endpoint(match.group("destination"))
    if not origin or not destination or origin.lower() == destination.lower():
        return ""
    if origin.lower() in {"airport", "hotel", "accommodation", "private airport"}:
        return ""
    return f"Private transfer from {origin} to {destination}"

def standardize_private_transfer_title(title, details, city):
    text = fix_common_text(details or title)
    lower = text.lower()

    # Generic supplier phrases are not named airports.  This decision belongs
    # to the transport domain rather than broad source/customer text cleanup.
    if re.search(r"\b(?:hotel|accommodation)\s+to\s+(?:the\s+)?airport\b", lower):
        return f"Private transfer from your hotel to {city_airport(city)}"
    if re.search(r"\bairport\s+to\s+(?:the\s+)?(?:hotel|accommodation)\b", lower):
        return f"Private transfer from {city_airport(city)} to your accommodation"

    airport = _explicit_airport_from_text(text, city)
    generic_route_title = _generic_private_transfer_route_title(text)

    if re.search(r"\bhotel\s+to\s+[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?\s+Airport\b", text, flags=re.IGNORECASE):
        return f"Private transfer from your hotel to {airport}"
    if re.search(r"\b[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?\s+Airport\s+to\s+hotel\b", text, flags=re.IGNORECASE):
        return f"Private transfer from {airport} to your accommodation"

    if "hotel to airport" in lower or "accommodation to airport" in lower:
        return f"Private transfer from your hotel to {airport}"

    if "airport to hotel" in lower or "airport to accommodation" in lower:
        return f"Private transfer from {airport} to your accommodation"

    if "hotel to cruise terminal" in lower or "hotel to terminal" in lower:
        return "Private transfer from your hotel to the cruise terminal"

    if "cruise terminal to hotel" in lower or "terminal to hotel" in lower or "terminal to accommodation" in lower:
        return "Private transfer from the cruise terminal to your accommodation"

    if "terminal to airport" in lower:
        return "Private transfer from the terminal to the airport"

    if re.search(r"\b(?:railway\s+)?station\s+to\s+(?:the\s+)?airport\b", lower):
        station = normalize_transport_place((city + " Railway Station").strip()) if city else "the railway station"
        return f"Private transfer from {station} to {airport}"

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

    if generic_route_title:
        return generic_route_title

    return fix_common_text(title)


def standardize_self_transfer_title(title, details, city):
    text = fix_common_text(details or title)
    lower = text.lower()
    airport = _explicit_airport_from_text(text, city)

    if "hotel to airport" in lower or "accommodation to airport" in lower or "to airport" in lower:
        return f"Self-arranged transfer from your hotel to {airport}"

    if "airport to hotel" in lower or "airport to accommodation" in lower:
        return f"Self-arranged transfer from {airport} to your accommodation"

    if "hotel to cruise" in lower or "hotel to harbor" in lower or "hotel to harbour" in lower:
        return "Self-arranged transfer from your hotel to the cruise harbour"

    if "cruise harbor to hotel" in lower or "cruise harbour to hotel" in lower or "cruise terminal to hotel" in lower:
        return "Self-arranged transfer from the cruise harbour to your accommodation"

    lyngen = re.search(r"to\s+(?:the\s+)?meeting point of\s+(.+?)(?:\.|$)", text, flags=re.IGNORECASE)
    if lyngen:
        destination = fix_common_text(lyngen.group(1)).strip(" -:|,.")
        return f"Self-arranged transfer to {destination}" if destination else "Self-arranged local transfer"

    if "activity meeting point" in lower or "activity location" in lower:
        return "Self-arranged transfer to activity location"

    if "bus station" in lower or "bustation" in lower:
        if "hotel to" in lower or "to bus" in lower:
            return "Self transfer from your hotel to the bus station"
        if "to hotel" in lower or "to accommodation" in lower or "station to" in lower:
            return "Self transfer from the bus station to your accommodation"

    if "hotel to station" in lower or "to station" in lower:
        return f"Self-arranged transfer from your hotel to {normalize_transport_place((city + ' Railway Station').strip()) if city else 'the railway station'}"

    if "station to hotel" in lower or "station to accommodation" in lower:
        return f"Self-arranged transfer from {normalize_transport_place((city + ' Railway Station').strip()) if city else 'the railway station'} to your accommodation"

    if "|" in text and "self" in lower and "transfer" in lower:
        return "Self-arranged local transfer"

    notes = split_self_transfer_notes(text)
    if notes:
        return re.sub(r"\s*\([^)]*(?:cheapest|efficient|taxi|local)[^)]*\)", "", notes[0], flags=re.IGNORECASE).strip()
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
    origin, destination = _explicit_transport_route_from_text(details)
    if not destination:
        origin, destination = _explicit_transport_route_from_text(title)
    if not destination:
        origin, destination = _explicit_transport_route_from_text(text)
    if not destination:
        origin, destination = extract_route_points(details)
    if not destination:
        origin, destination = extract_route_points(title)
    if not destination:
        origin, destination = extract_route_points(text)
    city = normalize_place_name(row.get("city", ""))
    destination = _compact_route_destination(destination, city)

    if "norway in a nutshell" in lower:
        return _norway_nutshell_route_label(text, origin, destination)

    if row_type == "Flight" or "flight" in lower:
        if destination:
            return f"Flight to {destination}"
        if city:
            return f"Flight to {city}"
        return "Flight"

    if row_type == "Train" or "train" in lower:
        prefix = "Santa Claus Express" if "santa claus express" in lower else ("Overnight Train" if re.search(r"\b(?:overnight|night)\s+train\b", lower) else "Train")
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

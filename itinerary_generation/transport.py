import re

from parser_modules.common import extract_route_points
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
    return (
        "airport" in text
        and (
            "to hotel" in text
            or "to accommodation" in text
            or "to your accommodation" in text
            or "to city centre" in text
            or "to city center" in text
        )
    )


def has_airport_departure_transfer(day_rows):
    text = " ".join(f'{row.get("title", "")} {row.get("details", "")}' for row in day_rows).lower()
    return ("airport" in text and ("hotel to" in text or "accommodation to" in text or "to airport" in text))


_ROUTE_PREFIX_ORIGINS = {
    "transfer", "train transfer", "scenic train transfer", "flight transfer",
    "coach transfer", "bus transfer", "long distance panorama coach transfer",
    "panoramic coach transfer", "coastal cruise", "overnight coastal cruise",
    "atlantic ocean cruise", "ferry transfer", "arrival", "overnight train", "train",
}


def _transport_source_text(row):
    return " ".join(
        str(row.get(key, "") or "")
        for key in ["title", "details", "original_title"]
        if str(row.get(key, "") or "").strip()
    )


def _clean_route_place(value):
    raw = str(value or "").strip(" -:|.,")
    raw = re.sub(r"^(?:from|to)\s+", "", raw, flags=re.IGNORECASE).strip(" -:|.,")
    raw = re.split(r"\s+-\s+|\s+\|\s+|\s+at\s+\d{1,2}:\d{2}|\s+\d{1,2}:\d{2}", raw, maxsplit=1, flags=re.IGNORECASE)[0].strip(" -:|.,")
    if re.search(r"fl[åa]msbanen", raw, flags=re.IGNORECASE):
        raw = "Flåm"
    if re.search(r"one[- ]?way geiranger fjord cruise", raw, flags=re.IGNORECASE):
        raw = "Ålesund"
    place = canonicalize_place_name(raw)
    lower = place.lower()
    if lower in _ROUTE_PREFIX_ORIGINS | {"", "hotel", "station", "airport", "accommodation", "your accommodation"}:
        return ""
    if any(marker in lower for marker in ["santa claus express", "downstairs cabin", "tickets included", "meal plan", "shower", "sink", "wc in carriage", "women's", "men's", "benefits", "made bed"]):
        return ""
    return place


def get_route_points_for_transport(row):
    """Return normalized (origin, destination) for a transport row.

    This is route-based rather than fixture-based. It looks across title,
    details and original text, because supplier cells often put the route in
    any of those locations.
    """
    source_text = _transport_source_text(row)
    station_match = re.search(r"\b([A-Za-zÀ-ÿøØåÅäÄöÖ ]+?)\s+(?:Central|station)\s*[–-]\s*([A-Za-zÀ-ÿøØåÅäÄöÖ ]+?)\s+station\b", source_text, flags=re.IGNORECASE)
    if station_match:
        return _clean_route_place(station_match.group(1)), _clean_route_place(station_match.group(2))

    plain_from_match = re.search(r"\bfrom\s+([A-Za-zÀ-ÿøØåÅäÄöÖ ]+?)\s+(?:Central|station)\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ ]+?)\s+(?:Central|station)\b", source_text, flags=re.IGNORECASE)
    if plain_from_match:
        return _clean_route_place(plain_from_match.group(1)), _clean_route_place(plain_from_match.group(2))

    # Prefer the parser-normalized title for destination, but enrich it with
    # origin from supplier details when the destination matches. This avoids
    # stale contradictory details while still producing useful route wording.
    title_origin, title_destination = extract_route_points(str(row.get("title", "") or ""))
    title_origin = _clean_route_place(title_origin)
    title_destination = _clean_route_place(title_destination)
    if title_destination:
        for key in ["details", "original_title"]:
            origin, destination = extract_route_points(str(row.get(key, "") or ""))
            origin = _clean_route_place(origin)
            destination = _clean_route_place(destination)
            if origin and destination and destination.lower() == title_destination.lower():
                return origin, title_destination
        return title_origin, title_destination

    for key in ["details", "original_title"]:
        origin, destination = extract_route_points(str(row.get(key, "") or ""))
        origin = _clean_route_place(origin)
        destination = _clean_route_place(destination)
        if destination:
            return origin, destination

    origin, destination = extract_route_points(_transport_source_text(row))
    origin = _clean_route_place(origin)
    destination = _clean_route_place(destination)
    if destination:
        return origin, destination

    return "", _clean_route_place(row.get("city", ""))


def get_route_via_points(row, origin="", destination=""):
    text = polish_client_text(_transport_source_text(row))
    points = []

    via_match = re.search(r"\bvia\s+([A-Za-zÀ-ÿøØåÅäÄöÖ\s]+?)(?:\s+-\s+|\s+\||,|$)", text, flags=re.IGNORECASE)
    if via_match:
        candidate = _clean_route_place(via_match.group(1))
        if candidate and candidate.lower() not in {origin.lower(), destination.lower()}:
            points.append(candidate)

    # Multi-leg phrasing such as Copenhagen to Malmö to Stockholm.
    route_match = re.search(r"\b(?:train|scenic train transfer|flight|coach|bus|ferry|cruise)(?:\s+transfer)?\s*[:|]?\s*(.+?\s+to\s+.+?)(?:\s+-\s+(?:departure|arrival|time|includes|included|excludes)\b|$)", text, flags=re.IGNORECASE)
    if route_match:
        route_text = route_match.group(1)
        pieces = [_clean_route_place(piece) for piece in re.split(r"\s+to\s+", route_text, flags=re.IGNORECASE)]
        pieces = [piece for piece in pieces if piece]
        if len(pieces) > 2:
            for piece in pieces[1:-1]:
                if piece.lower() not in {origin.lower(), destination.lower()} and piece not in points:
                    points.append(piece)

    if not points and re.search(r"\bmalm[øo]\b", text, flags=re.IGNORECASE) and destination.lower() != "malmö":
        points.append("Malmö")

    return points[:2]


def _via_suffix(via_points):
    if not via_points:
        return ""
    return ", via " + " and ".join(via_points)


def _is_norway_in_a_nutshell_text(text):
    lower = str(text or "").lower()
    if "norway in a nutshell" in lower:
        return True
    has_flam = any(marker in lower for marker in ["flåm", "flam", "flåmsbana", "flamsbana", "flåm train", "flam train", "flåm railway", "flam railway"])
    has_fjord = any(marker in lower for marker in ["nærøyfjord", "naeroyfjord", "fjord cruise", "gudvangen", "voss"])
    return has_flam and has_fjord


def _norway_nutshell_route_label(text, fallback_origin="", fallback_destination=""):
    route_match = re.search(r"\b(Bergen|Oslo|Fl[åa]m|Voss|Gudvangen|Myrdal)\s+to\s+(Bergen|Oslo|Fl[åa]m|Voss|Gudvangen|Myrdal)\b", str(text or ""), flags=re.IGNORECASE)
    if route_match:
        origin, destination = polish_title(route_match.group(1)), polish_title(route_match.group(2))
    else:
        origin, destination = fallback_origin, fallback_destination
    if origin and destination and origin.lower() != destination.lower():
        return f"Norway in a Nutshell from {origin} to {destination}"
    if destination:
        return f"Norway in a Nutshell to {destination}"
    return "Norway in a Nutshell"


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


def _route_destination_from_text(value):
    text = polish_client_text(value)
    if not text or " to " not in text.lower():
        return ""
    _, destination = extract_route_points(text)
    return canonicalize_place_name(destination) if destination else ""


def is_route_transfer(row):
    if get_row_type(row) != "Transfer":
        return False
    text = f'{row.get("title", "")} {row.get("details", "")}'
    lower = text.lower()
    if any(marker in lower for marker in ["private", "shuttle", "self transfer", "hotel to", "airport to", "to hotel", "to airport", "to station", "accommodation"]):
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
        return f"Coach Transfer to {destination}"
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

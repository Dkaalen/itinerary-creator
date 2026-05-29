"""Parser place and route parsing helpers."""

import re

from place_aliases import canonicalize_place_name, is_likely_service_text
from .text_cleanup import clean_space, fix_common_text
from .type_detection import looks_like_day, looks_like_date, looks_like_known_type

INVALID_CITY_MARKERS = [
    "private hotel",
    "private airport",
    "hotel to airport",
    "airport to hotel",
    "optional addon",
    "optional add on",
    "optinal addon",
    "addon on request",
    "flight ",
]


def is_valid_city_value(value):
    city = clean_space(value).strip(" .,-|:")
    if not city:
        return False
    lower = city.lower()
    if looks_like_day(city) or looks_like_known_type(city) or looks_like_date(city):
        return False
    if city.isdigit():
        return False
    if len(city) > 35:
        return False
    if is_likely_service_text(city):
        return False
    if any(marker in lower for marker in INVALID_CITY_MARKERS):
        return False
    if " to " in lower and any(word in lower for word in ["airport", "hotel", "station", "bergen", "copenhagen", "svol"]):
        return False
    return True


def normalize_place_name(value):
    place = fix_common_text(clean_space(value))
    place = place.strip(" .,-|:")

    # Remove service/product wording that should not appear in clean day titles.
    place = re.sub(r"^(Flight|Bus|Coach|Train|Transfer|Shuttle Transfer)\s+", "", place, flags=re.IGNORECASE)
    place = re.sub(r"\bArctic Resort\b", "", place, flags=re.IGNORECASE)
    place = re.sub(r"\bAirport\s+Airport\b", "Airport", place, flags=re.IGNORECASE)
    place = re.sub(r"\s+", " ", place).strip(" .,-|:")

    return canonicalize_place_name(place)


def extract_route_points(text):
    """Returns (origin, destination) from common route phrasings.

    The helper is deliberately route-based, not itinerary-specific. It handles
    simple transport rows ("Train: Oslo to Bergen") and multi-leg rows where an
    intermediate stop appears before the final destination ("Copenhagen to
    Malmö to Stockholm").
    """

    source = fix_common_text(text)
    source = source.replace("–", "-")

    # Trim supplier schedule/details so they do not become part of the city.
    route_source = re.split(
        r"\s+-\s+(?:departure|arrival|time|includes|included|excludes|luggage|cabin)\b|\s+\|\s+(?:departure|arrival|time|includes|included|excludes|final\s+timing|voucher)\b",
        source,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]

    prefix_origin = ""
    prefix_match = re.match(r"^([A-Za-zÀ-ÿøØåÅäÄöÖ\s]+):\s*(.+)$", route_source)
    if prefix_match and is_valid_city_value(prefix_match.group(1)):
        prefix_origin = normalize_place_name(prefix_match.group(1))
        route_source = prefix_match.group(2)

    # Explicit transport route with one or more "to" segments. Use the final
    # segment as destination, not an intermediate change point such as Malmö.
    transport_route = re.search(
        r"\b(?:flight|train|coach|bus|ferry|cruise)(?:\s+transfer)?\s*(?:[:|])?\s*(.+?\s+to\s+.+)$",
        route_source,
        flags=re.IGNORECASE,
    )
    if transport_route:
        route_text = clean_space(transport_route.group(1)).strip(" -:|.")
        if prefix_origin and route_text.lower().startswith("to "):
            route_text = f"{prefix_origin} {route_text}"
        pieces = [clean_space(part).strip(" -:|.") for part in re.split(r"\s+to\s+", route_text, flags=re.IGNORECASE) if clean_space(part).strip(" -:|.")]
        if len(pieces) >= 2:
            origin_raw = re.sub(r"^(?:scenic\s+)?(?:flight|train|coach|bus|ferry|cruise)(?:\s+transfer)?\s*[:|]?\s*", "", pieces[0], flags=re.IGNORECASE).strip(" -:|.")
            destination_raw = re.split(r"\s+-\s+(?:bus|coach|flight|train)\b|\s+bus\s+\d+\b|\s+time\b|\s+departure\b|\s+arrival\b|\s*\|", pieces[-1], maxsplit=1, flags=re.IGNORECASE)[0].strip(" -:|.")
            origin = normalize_place_name(origin_raw)
            if origin.lower() in {"", "flight", "train", "transfer", "coach", "bus", "ferry", "cruise", "scenic train", "scenic train transfer", "long distance panorama coach transfer", "atlantic ocean cruise", "arrival"}:
                origin = prefix_origin
            destination_raw = re.split(r"\s+onboard\b|\s+on\s+board\b|\s+at\s+\d{1,2}:\d{2}", destination_raw, maxsplit=1, flags=re.IGNORECASE)[0].strip(" -:|.")
            destination = normalize_place_name(destination_raw)
            if destination.lower() not in {"hotel", "station", "airport", "accommodation"} and not re.search(r"shared in voucher|final timing|voucher", destination, flags=re.IGNORECASE):
                return origin, destination

    patterns = [
        r"\bfrom\s+(.+?)\s+to\s+(.+?)(?:\s+-\s+|\s+\|\s+|,|$)",
        r"\|\s*([^|\n]+?)\s+to\s+([^|\n]+?)\s*(?:\||$)",
        r"\b([A-Za-zÀ-ÿøØåÅäÄöÖ\s]+?)\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ\s]+?)(?:\s+-\s+|\s+\|\s+|,|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, route_source, flags=re.IGNORECASE)
        if not match:
            continue

        origin_raw = re.sub(r"^(?:scenic\s+)?(?:flight|train|coach|bus|ferry|cruise)(?:\s+transfer)?\s*[:|]?\s*", "", match.group(1), flags=re.IGNORECASE).strip(" -:|.")
        destination_raw = re.split(r"\s+onboard\b|\s+on\s+board\b|\s+at\s+\d{1,2}:\d{2}|\s*\|", match.group(2), maxsplit=1, flags=re.IGNORECASE)[0].strip(" -:|.")
        origin = normalize_place_name(origin_raw)
        if origin.lower() in {"", "flight", "train", "transfer", "coach", "bus", "ferry", "cruise", "scenic train", "scenic train transfer", "long distance panorama coach transfer", "atlantic ocean cruise", "arrival"}:
            origin = prefix_origin
        destination = normalize_place_name(destination_raw)

        if destination.lower() in {"hotel", "station", "airport", "accommodation"} or re.search(r"shared in voucher|final timing|voucher", destination, flags=re.IGNORECASE):
            continue

        return origin, destination

    return "", ""


def city_airport(city):
    city = normalize_place_name(city)
    return f"{city} Airport" if city else "the airport"

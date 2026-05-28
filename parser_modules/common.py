# Shared parser constants and text/route helpers.
import hashlib
import re

from time_utils import format_duration_display

import diagnostics
from place_aliases import canonicalize_place_name, is_likely_service_text, normalize_place_text
from text_polish import polish_client_text, polish_hotel_name, polish_title, polish_inclusion_items


DETAIL_LABELS = [
    "Time",
    "Meeting point",
    "End point",
    "Includes",
    "Notable Sights",
    "Schedule",
    "Description",
    "Overview",
    "Luggage included",
]

DETAIL_MARKERS = [f" - {label}:" for label in DETAIL_LABELS]
DAY_PATTERN = re.compile(r"^day\s+\d+", re.IGNORECASE)
DATE_PATTERN = re.compile(r"^\d{1,2}[./-]\d{1,2}[./-]\d{2,4}$")
KNOWN_TYPES = {
    "arrival",
    "transfer",
    "transport",
    "hotel",
    "activity",
    "leisure",
    "departure",
    "train",
    "flight",
    "cruise",
    "ferry",
}


def clean_space(value):
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


def normalize_type(value):
    return clean_space(value).title()


def looks_like_day(value):
    return bool(DAY_PATTERN.match(clean_space(value)))


def looks_like_date(value):
    return bool(DATE_PATTERN.match(clean_space(value)))


def looks_like_known_type(value):
    return clean_space(value).lower() in KNOWN_TYPES


def is_optional_addon_header(value):
    text = clean_space(value).lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = clean_space(text)
    # Supplier sheets contain many typo variants: optional addon, optinal addon,
    # optional add-on, addon on request. Treat all as optional commercial items.
    has_optional = "optional" in text or "optinal" in text or "on request" in text
    has_addon = any(marker in text for marker in ["addon", "add on", "addons", "add ons", "add on request", "addon on request"])
    return has_optional and (has_addon or "on request" in text)


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


COMMON_TEXT_REPLACEMENTS = [
    (r"\bNUtshell\b", "Nutshell"),
    (r"\bNutsheel\b", "Nutshell"),
    (r"\bNorway\s+in\s+a\s+Nutshell\b", "Norway in a Nutshell"),
    (r"\bBrekafast\b", "Breakfast"),
    (r"\bOverngiht\b", "Overnight"),
    (r"\bBrekfast\b", "Breakfast"),
    (r"\bDoubel\b", "Double"),
    (r"\bArrnaged\b", "arranged"),
    (r"\binclueded\b", "included"),
    (r"\binclued\b", "included"),
    (r"\bBergent\b", "Bergen"),
    (r"\bSvolaver\b", "Svolvær"),
    (r"\bSVolaver\b", "Svolvær"),
    (r"\bSvolvaer\b", "Svolvær"),
    (r"\bSvoalvaer\b", "Svolvær"),
    (r"\bTrosmø\b", "Tromsø"),
    (r"\bTrosmo\b", "Tromsø"),
    (r"\bGothernburg\b", "Gothenburg"),
    (r"\bGothenbrug\b", "Gothenburg"),
    (r"\baccommodaiton\b", "accommodation"),
    (r"\binlcuded\b", "included"),
    (r"\bInlcuded\b", "Included"),
    (r"\bIncludse\b", "Includes"),
    (r"\bFull\s+Pention\b", "Full pension"),
    (r"\bFull\s+Pension\b", "Full pension"),
    (r"\bOptinal\b", "Optional"),
    (r"\bRecepion\b", "Reception"),
    (r"\bStaion\b", "Station"),
    (r"\bKriuna\b", "Kiruna"),
    (r"\bwitj\b", "with"),
    (r"\bTromso\b", "Tromsø"),
    (r"\bKakslauttenen\b", "Kakslauttanen"),
    (r"\b(\d{1,2})\s+:\s*(\d{2})", r"\1:\2"),
    (r"\bWi-FI\b", "Wi-Fi"),
    (r"\bPickupo\b", "Pick up"),
    (r"\bOtpions\b", "Options"),
    (r"\bticktes\b", "tickets"),
    (r"\bROute\b", "Route"),
    (r"\binlc\b", "incl"),
    (r"\b4Star\b", "4 Star"),
    (r"\b3Star\b", "3 Star"),
]

SUSPICIOUS_FRAGMENTS = [
    "brekafast",
    "brekfast",
    "arrnaged",
    "inclueded",
    "inclued",
    "doubel",
    "bergent",
    "svolaver",
    "svoalvaer",
    "nutsheel",
    "nutshel",
]


def fix_common_text(value):
    """Silently fixes small recurring spelling/capitalization issues in pasted itineraries."""

    text = str(value or "")

    for pattern, replacement in COMMON_TEXT_REPLACEMENTS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    text = normalize_place_text(text)
    text = polish_client_text(text)

    return clean_space(text) if "\n" not in text else text


def check_for_unknown_typos(text, context=""):
    """Warn if known suspicious fragments remain after normal cleanup."""

    lower = str(text or "").lower()

    for fragment in SUSPICIOUS_FRAGMENTS:
        if fragment in lower:
            diagnostics.warn(
                "possible_typo",
                f"Possible uncorrected typo '{fragment}' found after text cleaning" + (f" in {context}" if context else ""),
                raw_value=str(text or "")[:200],
            )

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
        r"\s+-\s+(?:departure|arrival|time|includes|included|excludes|luggage|cabin)\b|\s+\|\s+(?:departure|arrival|time|includes|included|excludes)\b",
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
            if destination.lower() not in {"hotel", "station", "airport", "accommodation"}:
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

        if destination.lower() in {"hotel", "station", "airport", "accommodation"}:
            continue

        return origin, destination

    return "", ""


def city_airport(city):
    city = normalize_place_name(city)
    return f"{city} Airport" if city else "the destination airport"


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

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
    if re.fullmatch(r"[\d\s.,]+", city):
        return False
    if re.search(r"\b\d+\s*[-/]\s*\d+\s*[- ]?star\b|\b\d+\s*[- ]?star\s+hotel\b", lower):
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

    # Remove commercial/admin wording that can trail route places in supplier cells.
    place = re.sub(r"\bself[-\s]*(?:arranged|arrange|arrnaged|arrnage)\b", "", place, flags=re.IGNORECASE)
    place = re.sub(r"\b(?:cost|price)\s+not\s+in(?:cl|lc)uded\b", "", place, flags=re.IGNORECASE)
    place = re.sub(r"\bnot\s+included\b", "", place, flags=re.IGNORECASE)

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
    # Real calculator rows occasionally miss the ``t`` in ``to``:
    # ``Flight Bergen o Svolvær self-arranged``. Repair only when a transport
    # mode and two capitalized place-looking tokens are present.
    source = re.sub(
        r"\b(Flight|Train|Coach|Bus|Cruise|Ferry)\s+([A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{1,35}?)\s+o\s+([A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{1,35}?)(?=\s+(?:self[-\s]*arranged|cost|price)|\s*$)",
        r"\1 \2 to \3",
        source,
        flags=re.IGNORECASE,
    )

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

    route_source = re.sub(r"\bself[-\s]*(?:arranged|arrange|arrnaged|arrnage)\b", "", route_source, flags=re.IGNORECASE)
    route_source = re.sub(r"\b(?:cost|price)\s+not\s+in(?:cl|lc)uded\b", "", route_source, flags=re.IGNORECASE)


    scheduled_places = []
    for schedule_match in re.finditer(
        r"\b\d{1,2}[:.]\s*\d{2}(?:\s*[ap]m)?\s+(?P<place>[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{1,45}?)(?=\s+(?:via|direct|arrival|with|\d{1,2}[:.]\s*\d{2})|\s*[|,;)]|\s*$)",
        route_source,
        flags=re.IGNORECASE,
    ):
        place = normalize_place_name(schedule_match.group("place"))
        if place and is_valid_city_value(place) and place.lower() not in {"am", "pm", "morning train"}:
            scheduled_places.append(place)

    has_timed_dash_route = re.search(
        r"\d{1,2}[:.]\s*\d{2}\s+[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,45}?\s*-\s*\d{1,2}[:.]\s*\d{2}",
        route_source,
        flags=re.IGNORECASE,
    )
    if len(scheduled_places) >= 2 and not has_timed_dash_route and re.search(r"\b(?:norway\s+in\s+a\s+nutshell|train|flight|bus|coach|ferry|cruise)\b", route_source, flags=re.IGNORECASE):
        origin = scheduled_places[0]
        destination = scheduled_places[-1]
        if origin.lower() != destination.lower():
            return origin, destination

    bare_mode_route = re.search(
        r"^\s*(?:train|bus|coach|flight)\s+(?P<origin>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35}?)\s+(?P<destination>[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35}?)(?:\s*[|,;.]|\s+\d|$)",
        route_source,
        flags=re.IGNORECASE,
    )
    if bare_mode_route:
        origin = normalize_place_name(bare_mode_route.group("origin"))
        destination = normalize_place_name(bare_mode_route.group("destination"))
        if origin and destination and origin.lower() != destination.lower():
            return origin, destination


    nutshell_route = re.search(
        r"^\s*(?P<origin>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35}?)\s+to\s+(?P<destination>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35}?):\s*Norway\s+in\s+a\s+Nutshell\b",
        route_source,
        flags=re.IGNORECASE,
    )
    if nutshell_route:
        origin = normalize_place_name(nutshell_route.group("origin"))
        destination = normalize_place_name(nutshell_route.group("destination"))
        if origin and destination and origin.lower() != destination.lower():
            return origin, destination

    timed_legs = list(re.finditer(
        r"\b(?:bus|coach|train|flight|ferry|cruise)\s+\d{1,2}[:.]\s*\d{2}\s+(?P<origin>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35}?)\s*-\s*\d{1,2}[:.]\s*\d{2}\s+(?P<destination>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35}?)(?=\s*(?:\+|\||\(|$))",
        route_source,
        flags=re.IGNORECASE,
    ))
    if timed_legs:
        origin = normalize_place_name(timed_legs[0].group("origin"))
        destination = normalize_place_name(timed_legs[-1].group("destination"))
        if origin and destination and origin.lower() != destination.lower():
            return origin, destination

    night_train_route = re.search(
        r"(?P<origin>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35}?)\s*-\s*(?P<destination>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35}?)\s+Night\s+train\b",
        route_source,
        flags=re.IGNORECASE,
    )
    if night_train_route and re.search(r"\btrain\b", route_source, flags=re.IGNORECASE):
        origin = normalize_place_name(night_train_route.group("origin"))
        destination = normalize_place_name(night_train_route.group("destination"))
        if origin and destination and origin.lower() != destination.lower():
            return origin, destination

    reaching_route = re.search(
        r"\bfrom\s+(?P<origin>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35}?)(?:\s+bus\s+st(?:a|sa)ion|\s+station)?\b.+?\breaching\s+(?P<destination>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35}?)(?:\s+at\b|\s+resort\b|\s*[,|.]|$)",
        route_source,
        flags=re.IGNORECASE,
    )
    if reaching_route:
        origin = normalize_place_name(reaching_route.group("origin"))
        destination = normalize_place_name(reaching_route.group("destination"))
        if origin and destination and origin.lower() != destination.lower():
            return origin, destination

    # Hyphen-format transport rows from calculator exports, e.g.
    # ``Day train, Rovaniemi - Helsinki`` or ``Flight, Bergen - Svolvær``.
    dash_route = re.search(
        r"\b(?:day\s+|overnight\s+)?(?:train|flight|coach|bus|cruise|ferry)\b[^\n|,;:]{0,20}[,:]?\s+(?P<origin>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35}?)\s*-\s*(?P<destination>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35}?)(?:\n|\s+(?:intercity|ic|train|flight|coach|bus|cruise|ferry|self[-\s]*arranged|cost|price)\b|\s+\d{1,2}:\d{2}|$)",
        route_source,
        flags=re.IGNORECASE,
    )
    if dash_route:
        origin = normalize_place_name(dash_route.group("origin"))
        destination = normalize_place_name(dash_route.group("destination"))
        if origin and destination and origin.lower() != destination.lower():
            return origin, destination

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
            destination_raw = re.split(r"\s+part\s+\d+\b|\s+\d{1,2}:\d{2}|\s+-\s+(?:bus|coach|flight|train)\b|\s+bus\s+\d+\b|\s+time\b|\s+departure\b|\s+arrival\b|\s*\|", pieces[-1], maxsplit=1, flags=re.IGNORECASE)[0].strip(" -:|.")
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
        destination_raw = re.split(r"\s+part\s+\d+\b|\s+\d{1,2}:\d{2}|\s+onboard\b|\s+on\s+board\b|\s+at\s+\d{1,2}:\d{2}|\s*\|", match.group(2), maxsplit=1, flags=re.IGNORECASE)[0].strip(" -:|.")
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

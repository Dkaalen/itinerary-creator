import re

from itinerary_generation.common import (
    get_day_count,
    get_primary_city,
    get_row_type,
    get_unique_cities,
    get_destination_countries,
    has_self_drive_markers,
    clean_client_title,
    main_rows_only,
    has_hotel,
)
from parser_modules.common import extract_route_points
from itinerary_generation.transport import (
    get_primary_transport_title,
    has_airport_arrival_transfer,
    has_only_departure_arrangements,
)
from text_polish import strip_price_fragments, polish_title
from place_aliases import country_for_place
from itinerary_generation.cover_theme import (
    SEASON_LABELS,
    SEASON_SUBTITLES,
    SEASON_TITLES,
    detect_cover_season,
    has_winter_focus,
)


def _route_label_from_activity_text(text: str) -> str:
    route_match = re.search(r"\b(Bergen|Oslo|Fl[åa]m|Voss|Gudvangen|Myrdal)\s+to\s+(Bergen|Oslo|Fl[åa]m|Voss|Gudvangen|Myrdal)\b", text, flags=re.IGNORECASE)
    if route_match:
        origin, destination = route_match.group(1), route_match.group(2)
    else:
        origin, destination = extract_route_points(text)
    origin = polish_title(origin) if origin else ""
    destination = polish_title(destination) if destination else ""
    if origin and destination and origin.lower() != destination.lower():
        return f"Norway in a Nutshell from {origin} to {destination}"
    if destination:
        return f"Norway in a Nutshell to {destination}"
    return "Norway in a Nutshell"


def _looks_like_norway_in_a_nutshell(text: str) -> bool:
    lower = str(text or "").lower()
    if "norway in a nutshell" in lower:
        return True
    has_flam = any(marker in lower for marker in ["flåm", "flam", "flåmsbana", "flamsbana", "flåm train", "flam train", "flåm railway", "flam railway"])
    has_fjord = any(marker in lower for marker in ["nærøyfjord", "naeroyfjord", "fjord cruise", "gudvangen", "voss"])
    has_route = bool(re.search(r"\b(?:bergen|oslo|fl[åa]m|voss|gudvangen|myrdal)\b.+\bto\b.+\b(?:bergen|oslo|fl[åa]m|voss|gudvangen|myrdal)\b", lower))
    return has_flam and has_fjord and has_route



def _extract_supplier_day_heading(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""
    first_line = next((line.strip() for line in raw.splitlines() if line.strip()), "")
    match = re.match(r"^Day\s+\d+\s*[:\-–]\s*(.+)$", first_line, flags=re.IGNORECASE)
    if not match:
        return ""
    heading = re.split(r"\s{2,}|\s+Overview\b|\s+What's included\b|\s+What’s included\b|\s+What to expect\b", match.group(1), maxsplit=1, flags=re.IGNORECASE)[0]
    heading = re.split(
        r"\s+(?:We start|You will|You are|Prepare to|The first|A \d|At \w+|Once you|Afterwards|On your way)\b",
        heading,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    heading = heading.strip(" -:|.,")
    if re.search(r"J[öo]kuls[áa]rl[óo]n", heading, flags=re.IGNORECASE) and "ice" in heading.lower():
        heading = "Explore Jökulsárlón Glacier Lagoon & Ice Caves"
    return polish_title(heading)


BAD_TITLE_PATTERNS = [
    r"\barrival\s+[^,|]+,\s*pick[-\s]?up\b",
    r"\bpick[-\s]?up\s+minibus\b",
    r"\bpick[-\s]?up\s*/\s*drop[-\s]?off\b",
    r"\bprivate\s+(?:airport|hotel|station)\s+to\b",
    r"\bshuttle\s*/?\s*flybus\b",
    r"\bwith\s+transfers?\b",
    r"\bcost\s+not\s+included\b",
    r"\bself[-\s]?arranged\b",
    r"\bwhat'?s\s+included\b",
    r"\boverview\b",
]


def is_bad_raw_day_title(title: str) -> bool:
    text = str(title or "").strip()
    if not text:
        return True
    lower = text.lower()
    if len(text) > 85:
        return True
    return any(re.search(pattern, lower, flags=re.IGNORECASE) for pattern in BAD_TITLE_PATTERNS)



def normalize_client_day_title(title: str, row: dict | None = None) -> str:
    """Polish recurring supplier/admin titles into client-facing day titles.

    This is deliberately pattern-based rather than fixture-based. It handles
    common supplier wording across inputs while preserving proper product names.
    """
    source = strip_price_fragments(title or "")
    text = polish_title(clean_client_title(source))
    full = f"{text} {(row or {}).get('title', '')} {(row or {}).get('original_title', '')} {(row or {}).get('details', '')}".lower()

    text = re.sub(r"^Accommodation\s*:\s*Check[- ]?in\s+at\s+", "", text, flags=re.IGNORECASE).strip(" -:|")
    text = re.sub(r"\s+(?:with|incl\.?|including)\s+transfers?\b", "", text, flags=re.IGNORECASE).strip(" -:|")
    text = re.sub(r"\bWatch\s+Whales\b", "Whale Watching", text, flags=re.IGNORECASE)

    if re.search(r"\bessential\s+oslo\b|\boslo\s*:\s*.*city\s+cent(?:er|re).*walking", full, flags=re.IGNORECASE):
        return "Oslo Walking Tour"
    if re.search(r"\ba\s+city\s+walk\s+in\s+the\s+old\s+town\b|old town.*famous attractions", full, flags=re.IGNORECASE):
        if "stockholm" in full:
            return "Stockholm Old Town Walking Tour"
        return "Old Town Walking Tour"
    if re.search(r"\btransported\s+tour\b.*runic|runic kingdom", full, flags=re.IGNORECASE):
        return "Runic Kingdom & Viking History Tour"
    if "secret food" in full and "copenhagen" in full:
        return "Copenhagen Food Tour"
    if "fløibanen" in full or "floibanen" in full:
        return "Fløibanen Funicular"
    if "santa's igloos" in full or "glass igloo" in full:
        return "Glass Igloo Stay in Rovaniemi"

    if _looks_like_norway_in_a_nutshell(full):
        route_label = _route_label_from_activity_text(full)
        # Day titles read better with the destination focus; inclusions can keep
        # the full from/to route wording.
        dest_match = re.search(r"\bto\s+([A-Za-zÀ-ÿøØåÅäÄöÖ]+)\s*$", route_label)
        if dest_match:
            return f"Norway in a Nutshell to {polish_title(dest_match.group(1))}"
        return route_label

    return polish_title(text)

def create_client_activity_title(row):
    title = clean_client_title(strip_price_fragments(row.get("title", "")))
    original_title = clean_client_title(strip_price_fragments(row.get("original_title", "") or title))
    details = str(row.get("details", "") or "")

    supplier_heading = _extract_supplier_day_heading(row.get("original_title") or details)
    if supplier_heading and (title.lower().startswith("guided experience") or is_bad_raw_day_title(title)):
        title = supplier_heading

    if not title:
        for segment in re.split(r"\s*\|\s*|\s+-\s+", details):
            candidate = clean_client_title(strip_price_fragments(segment))
            if candidate and not candidate.lower().startswith(("optional addon", "optional add-on", "optional add on")):
                title = candidate
                break

    title_text = str(title or original_title or "").lower()
    original_title_text = str(original_title or "").lower()
    full_text = f"{title_text} {original_title_text} {details}".lower()

    title = re.sub(r"\s+(?:with|incl\.?|including)\s+transfers?\b", "", str(title or ""), flags=re.IGNORECASE).strip(" -:|")
    title = re.sub(r"^Watch\s+Whales\b", "Whale Watching", title, flags=re.IGNORECASE).strip()
    title_text = title.lower()
    full_text = f"{title_text} {original_title_text} {details}".lower()

    if _looks_like_norway_in_a_nutshell(f"{original_title} {title} {details}"):
        return _route_label_from_activity_text(f"{original_title} {title} {details}")

    if "santa claus" in full_text and "friends" in full_text:
        return "Meet Santa Claus and his friends"

    if "blue lagoon" in full_text or "bluelagoon" in full_text:
        if any(marker in title_text for marker in ["volcano", "eruption", "fagradalsfjall"]):
            return polish_title(title)
        if "premium" in full_text:
            return "Blue Lagoon Premium Admission"
        return "Blue Lagoon Admission"

    if "sky lagoon" in full_text or "skylagoon" in full_text:
        if "saman" in full_text or "7-step" in full_text or "7 step" in full_text:
            return "Sky Lagoon Saman Pass & 7-Step Ritual"
        return "Sky Lagoon Admission"

    if "silfra" in full_text and ("snork" in full_text or "drysuit" in full_text):
        return "Drysuit Snorkelling in Silfra"

    if "whale watching" in full_text:
        if "arctic wildlife" in full_text or "rib boat" in full_text or "wildlife safari" in full_text:
            return "Whale Watching & Arctic Wildlife Safari"
        if "from downtown" in full_text:
            return "Whale Watching From Downtown"
        return "Whale Watching"

    if "tallinn" in full_text:
        return "Day Trip to Tallinn"

    if "optional addon" in full_text and any(marker in full_text for marker in ["svolvær", "svolvaer", "svolaver", "svoalvaer"]):
        return "Optional experience in Svolvær"

    if "lofoten" in full_text and "trollfjord" in full_text:
        return "Lofoten Day Tour & Trollfjord Cruise"

    if "fløibanen" in full_text or "floibanen" in full_text:
        return "Fløibanen Funicular"

    if "arctic route" in full_text or "senja" in full_text and "coach" in full_text:
        return "Arctic Route Coach Transfer"

    if "hop-on" in title_text or "hop off" in title_text or "hop-off" in title_text or "hop on hop off" in full_text:
        if "copenhagen" in full_text:
            return "Copenhagen Hop-On Hop-Off Bus Ticket"
        if "bergen" in full_text:
            return "Bergen Hop-On Hop-Off Bus Ticket"
        return "Hop-On Hop-Off Bus Ticket"

    if "city walking" in full_text and "canal" in full_text and "copenhagen" in full_text:
        return "Copenhagen Walking & Canal Tour"

    if "wildlife photography" in full_text and "longyearbyen" in full_text:
        return "Wildlife Photography Around Longyearbyen"
    if "wildlife and glacier" in full_text:
        return "Wildlife & Glacier Experience"
    if "mountain hike" in full_text and "abisko" in full_text:
        return "Mountain Hike in Abisko"
    if "round trip ticket" in full_text and "trom" in full_text:
        return "Fjellheisen Cable Car"

    if title_text.startswith("round trip ticket"):
        return "Round Trip Ticket"

    title_has_northern_lights = (
        "northern light" in title_text
        or "aurora" in title_text
        or "borealis" in title_text
    )
    full_has_northern_lights = (
        "northern light" in full_text
        or "aurora" in full_text
        or "borealis" in full_text
    )
    title_has_northern_lights_activity_word = any(
        word in title_text
        for word in ["hunt", "chase", "basecamp", "base camp", "cruise", "boat", "float", "floating", "mileage"]
    )

    # Do not rename ordinary daytime/culture activities just because the long
    # supplier description mentions a chance of seeing northern lights.
    is_northern_lights = title_has_northern_lights or (
        full_has_northern_lights and title_has_northern_lights_activity_word
    )

    if not is_northern_lights:
        return title

    if "reindeer" in full_text and ("hunt" in full_text or "hunting" in full_text or "chase" in full_text):
        return "Northern Lights Hunt by Reindeer"

    if "basecamp" in full_text or "base camp" in full_text:
        return "Northern Lights Basecamp"

    if "cruise" in full_text or "boat" in full_text or "sailing" in full_text:
        return "Northern Lights Cruise"

    if "floating" in full_text or "float" in full_text:
        return "Northern Lights Ice Floating"

    if "chase" in full_text:
        return "Northern Lights Chase"

    if "hunt" in full_text or "mileage" in full_text or "photo tour" in full_text:
        return "Northern Lights Hunt"

    return "Northern Lights Experience"


def create_trip_title(parsed_rows, grouped_days):
    parsed_rows = main_rows_only(parsed_rows)
    cities = get_unique_cities(parsed_rows)
    day_count = get_day_count(grouped_days)
    season = detect_cover_season(parsed_rows)
    season_label = SEASON_LABELS.get(season, "Summer")
    countries = get_destination_countries(parsed_rows)
    text = " ".join(f'{row.get("title", "")} {row.get("original_title", "")} {row.get("details", "")}' for row in parsed_rows).lower()

    is_group_tour = any(marker in text for marker in ["group tour", "holiday package", "sharing room basis"])
    has_cruise_heavy = sum(1 for row in parsed_rows if get_row_type(row) == "Cruise") >= 3
    has_nutshell = "norway in a nutshell" in text or ("flåm" in text or "flam" in text) and ("nærøyfjord" in text or "naeroyfjord" in text)
    has_aurora = any(marker in text for marker in ["northern light", "aurora", "icehotel", "kiruna", "svalbard", "lapland"])
    has_western_norway = set(cities).intersection({"Bergen", "Ålesund", "Geiranger", "Solvorn", "Flåm", "Myrdal"}) and len(set(cities)) >= 3 and countries == ["Norway"]

    if is_group_tour and countries == ["Iceland"]:
        if "snæfellsnes" in text or "snaefellsnes" in text:
            return "Snæfellsnes & South Coast Adventure"
        return "Iceland Guided Discovery"

    if has_western_norway:
        return "Western Norway Scenic Escape"
    if has_cruise_heavy and len(countries) >= 2:
        return "Scandinavian Coastal Voyage" if set(countries).issubset({"Norway", "Sweden", "Denmark"}) else "Nordic Coastal Voyage"
    if has_aurora and countries == ["Sweden"]:
        return "Swedish Lapland Aurora Break"
    if has_aurora and countries == ["Norway"] and any(city in cities for city in ["Tromsø", "Svalbard", "Kiruna"]):
        return "Arctic Norway Adventure"
    if has_nutshell and countries == ["Norway"]:
        return "Norway Fjord & Rail Journey"

    if len(countries) == 1:
        country = countries[0]
        if season in {"spring", "summer", "autumn"}:
            return f"{country} {season_label} Escape"
        return f"{country} {season_label} Journey"

    scandinavian = {"Norway", "Sweden", "Denmark"}
    nordic = scandinavian | {"Finland", "Iceland", "Estonia"}
    country_set = set(countries)
    if len(country_set) >= 2 and country_set.issubset(scandinavian):
        return f"Scandinavian {season_label} Discovery"
    if len(country_set) >= 2 and country_set.issubset(nordic):
        if has_aurora:
            return "Lapland & Norway Northern Lights Escape"
        return f"Nordic {season_label} Highlights"

    if len(cities) == 1:
        city = cities[0]
        if has_aurora:
            return f"{city} Northern Lights Journey"
        return f"{city} {season_label} Journey"

    if len(cities) >= 2:
        return SEASON_TITLES.get(season, f"{season_label} Journey")

    if day_count >= 10:
        return "Grand Nordic Journey"

    return "Nordic Discovery Journey"


def _join_destinations_naturally(cities):
    clean_cities = [str(city or "").strip() for city in cities if str(city or "").strip()]
    if not clean_cities:
        return "the Nordics"
    if len(clean_cities) == 1:
        return clean_cities[0]
    if len(clean_cities) == 2:
        return f"{clean_cities[0]} and {clean_cities[1]}"
    return ", ".join(clean_cities[:-1]) + f" and {clean_cities[-1]}"


def create_trip_subtitle(parsed_rows, grouped_days):
    parsed_rows = main_rows_only(parsed_rows)
    season = detect_cover_season(parsed_rows)
    season_label = SEASON_LABELS.get(season, "summer").lower()
    countries = get_destination_countries(parsed_rows)
    scope = countries[0] if len(countries) == 1 else "Nordic"
    if has_self_drive_markers(parsed_rows):
        return f"A premium {scope} {season_label} self-drive journey with scenic routes and curated experiences"
    if season in SEASON_SUBTITLES:
        if len(countries) == 1:
            return f"A premium {scope} {season_label} journey with scenic travel and curated experiences"
        return SEASON_SUBTITLES[season]
    if has_winter_focus(parsed_rows):
        return SEASON_SUBTITLES["winter"]
    return "A carefully arranged Nordic journey with seamless travel and curated experiences"

def create_destinations_line(parsed_rows):
    cities = get_unique_cities(parsed_rows)

    if not cities:
        return "Destinations will be detected from the itinerary text"

    return " · ".join(cities)


def create_day_title(day_rows):
    city = get_primary_city(day_rows)

    has_arrival = any(get_row_type(row) == "Arrival" for row in day_rows)
    has_departure = any(get_row_type(row) == "Departure" for row in day_rows)
    hotel_present = has_hotel(day_rows)
    transport_title = get_primary_transport_title(day_rows)
    activity_rows = [row for row in day_rows if get_row_type(row) == "Activity"]
    overview_rows = [row for row in day_rows if get_row_type(row) == "Day Overview"]

    if has_only_departure_arrangements(day_rows) and city:
        return f"Departure from {city}"

    if has_arrival and city:
        return f"Welcome to {country_for_place(city) or city}" if country_for_place(city) == "Iceland" else f"Welcome to {city}"

    # Colleague format often starts with a transfer + hotel, without an explicit
    # Arrival row. Treat airport/city-centre transfer + accommodation as arrival
    # before allowing the transfer text to become the title.
    if hotel_present and not activity_rows and has_airport_arrival_transfer(day_rows) and city:
        return f"Welcome to {country_for_place(city) or city}" if country_for_place(city) == "Iceland" else f"Welcome to {city}"

    # Real day/activity headings should beat supplier overview snippets such as
    # "Day 1: Arrival Reykjavík, pick-up minibus". Those snippets are useful
    # logistics, but they are not premium client-facing day titles.
    if activity_rows:
        title = create_client_activity_title(activity_rows[0])
        if title and not is_bad_raw_day_title(title):
            return normalize_client_day_title(title, activity_rows[0])

    # Day overview rows may drive the title only when no better activity title
    # exists, and never when they look like admin/logistics copy.
    for overview in overview_rows:
        overview_text = f'{overview.get("title", "")} {overview.get("details", "")}'.strip()
        lower_overview = overview_text.lower()
        if re.search(r"rental\s+(?:vehicle|car|suv)|pick\s*up\s+rental|pickup\s+rental|drop\s+vehicle|return\s+vehicle", lower_overview):
            continue
        match = re.search(r"\bDay\s*\d+\s*:\s*([^\n|]+)", overview_text, flags=re.IGNORECASE)
        if match:
            candidate = clean_client_title(match.group(1).strip())
            if not is_bad_raw_day_title(candidate):
                return candidate

    # Travel days with a hotel check-in should be titled by the main travel
    # movement rather than by a later evening activity or transfer.
    if hotel_present and transport_title:
        return transport_title

    if has_departure and city:
        return f"Departure from {city}"

    if transport_title:
        return transport_title

    priority_order = [
        "Transfer",
        "Hotel",
        "Leisure",
    ]

    for item_type in priority_order:
        for row in day_rows:
            if get_row_type(row) == item_type:
                title = row.get("title", "").strip()
                if item_type == "Hotel":
                    hotel_text = f'{row.get("hotel_name", "")} {row.get("room_category", "")} {row.get("details", "")}'
                    if re.search(r"glass\s+igloo|santa's\s+igloos", hotel_text, flags=re.IGNORECASE):
                        return "Glass Igloo Stay in Rovaniemi"
                    if city:
                        return f"Stay in {city}"

                if title:
                    clean_title = normalize_client_day_title(title, row)
                    return clean_title or title

    return "Day at leisure"

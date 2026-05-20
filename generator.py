from collections import OrderedDict
import re

from place_aliases import canonicalize_place_name, is_likely_service_text
from text_polish import polish_client_text, polish_title, polish_inclusion_item


TRANSPORT_TYPES = ["Transport", "Train", "Flight", "Cruise", "Ferry"]

DETAIL_LEVELS = [
    "Elegant concise",
    "Standard client itinerary",
    "Rich descriptive",
]


def normalize_detail_level(value):
    value = str(value or "").strip()
    if value in DETAIL_LEVELS:
        return value
    return "Standard client itinerary"


def get_row_city(day_rows):
    city = get_primary_city(day_rows)
    return city or "the destination"


def get_client_activity_phrase(row):
    title = create_client_activity_title(row) or row.get("title", "your included experience")
    return title or "your included experience"


def get_row_type(row):
    return row.get("effective_type") or row.get("type", "")


def get_day_number(day_text):
    digits = "".join(character for character in str(day_text) if character.isdigit())

    if digits:
        return int(digits)

    return 0


def group_rows_by_day(parsed_rows):
    grouped = {}

    for row in parsed_rows:
        if is_optional_row(row):
            continue

        day = row.get("day", "Unknown day")

        if day not in grouped:
            grouped[day] = []

        grouped[day].append(row)

    return OrderedDict(
        sorted(
            grouped.items(),
            key=lambda item: get_day_number(item[0]),
        )
    )


def get_day_count(grouped_days):
    return len(grouped_days)


def add_unique(items, item):
    clean_item = str(item or "").strip()

    if clean_item and clean_item not in items:
        items.append(clean_item)


def is_optional_row(row):
    return bool(row.get("is_optional"))


def main_rows_only(rows):
    return [row for row in rows if not is_optional_row(row)]


def optional_rows_only(rows):
    return [row for row in rows if is_optional_row(row)]


def is_valid_destination_city(city):
    city = canonicalize_place_name(str(city or "").strip())
    if not city:
        return False
    lower = city.lower()
    invalid_markers = [
        "private hotel",
        "private airport",
        "hotel to airport",
        "airport to hotel",
        "optional addon",
        "optional add",
        "flight ",
        "hop on hop off",
        "hop-on hop-off",
        "24 hrs ticket",
        "24 hour ticket",
        "option private sightseeing",
        "private sightseeing",
        "private tour",
        "cancel hop on hop off",
        "ticket",
    ]
    if is_likely_service_text(city):
        return False
    if any(marker in lower for marker in invalid_markers):
        return False
    if " to " in lower and any(word in lower for word in ["airport", "hotel", "station", "bergen", "copenhagen", "svol"]):
        return False
    return True


def clean_client_title(value):
    """Small client-facing title cleanup used after parsing."""

    title = str(value or "").strip()
    if not title:
        return ""

    # Remove over-marketing phrases that should not appear in polished itineraries.
    cleanup_phrases = [
        "with 97% Success Rate",
        "with Pro Photos Included",
        "with Pro Photographer",
        "with Professional Photographer",
        "Included",
    ]

    for phrase in cleanup_phrases:
        title = title.replace(phrase, "")

    title = title.replace("  ", " ").strip(" -:|")
    return title


def get_activity_text(row):
    return f'{row.get("original_title", "")} {row.get("title", "")} {row.get("details", "")}'.lower()


def has_hotel(day_rows):
    return any(get_row_type(row) == "Hotel" for row in day_rows)


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

    # Use the last route-like destination in the string. This works for messy
    # rows such as "Tromsø to Bergen" or "Flight Bergen to Svolvær".
    matches = list(re.finditer(r"\bfrom\s+(.+?)\s+to\s+([^|,.;\n]+)|\b([^|,.;\n]+?)\s+to\s+([^|,.;\n]+)", text, flags=re.IGNORECASE))
    if not matches:
        return ""

    match = matches[-1]
    destination = match.group(2) or match.group(4) or ""
    destination = destination.strip(" -:|.")
    # Remove trailing supplier/status text.
    destination = re.split(r"\s+(?:self|cost|price|not|included|arranged)\b", destination, flags=re.IGNORECASE)[0].strip(" -:|.")
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


def get_unique_cities(parsed_rows):
    cities = []

    for row in parsed_rows:
        if is_optional_row(row):
            continue

        city = canonicalize_place_name(row.get("city", "").strip())

        if is_valid_destination_city(city) and city not in cities:
            cities.append(city)

    return cities


def is_self_arranged(row):
    text = f'{row.get("title", "")} {row.get("details", "")}'.lower()
    row_type = get_row_type(row)

    # Activity descriptions often contain exclusions like "guide not included"
    # or "food and drinks not included". Those should not turn the whole
    # experience into self-arranged travel.
    if row_type == "Activity":
        return False

    markers = [
        "self arranged",
        "self-arranged",
        "self arrnaged",
        "cost not included",
        "cost not inclueded",
        "price not included",
        "flight cost not",
    ]

    return any(marker in text for marker in markers)


def get_primary_city(day_rows):
    """
    Prefer the city of the main hotel/activity for mixed transfer days.
    This avoids days like Tromsø -> Bergen showing only the departure city.
    """

    if not day_rows:
        return ""

    priority_types = ["Hotel", "Flight", "Train", "Transport", "Cruise", "Ferry", "Activity", "Arrival", "Departure", "Transfer"]

    for preferred_type in priority_types:
        for row in day_rows:
            if get_row_type(row) == preferred_type:
                city = canonicalize_place_name(row.get("city", "").strip())
                if city and is_valid_destination_city(city):
                    return city

    return canonicalize_place_name(day_rows[0].get("city", "").strip())


def get_travel_destination_city(day_rows):
    """Prefer the actual route destination for travel-led day intros."""
    for row in day_rows:
        if get_row_type(row) in TRANSPORT_TYPES or is_route_transfer(row):
            title = row.get("title", "")
            match = re.search(r"\bto\s+([A-Za-zÀ-ÿøØåÅäÄöÖæÆ .'-]+)$", title, flags=re.IGNORECASE)
            if match:
                destination = canonicalize_place_name(match.group(1).strip(" .,-|:"))
                if destination and is_valid_destination_city(destination):
                    return destination
            text = f'{row.get("title", "")} {row.get("details", "")}'
            destination = _route_destination_from_text(text)
            if destination and is_valid_destination_city(destination):
                destination = re.split(r"\s+(?:overnight|flight|train|cruise|ferry|arrival|at)\b", destination, maxsplit=1, flags=re.IGNORECASE)[0].strip()
                destination = canonicalize_place_name(destination)
                if destination and is_valid_destination_city(destination):
                    return destination
    return get_primary_city(day_rows)


def create_client_activity_title(row):
    title = clean_client_title(row.get("title", ""))
    original_title = clean_client_title(row.get("original_title", "") or title)
    details = str(row.get("details", "") or "")

    title_text = f"{original_title} {title}".lower()
    full_text = f"{title_text} {details}".lower()
    city = canonicalize_place_name(row.get("city", ""))

    departure_markers = ["check out", "transfer to the airport", "drop at the airport", "return flight", "bound for home", "packed breakfast"]
    if sum(1 for marker in departure_markers if marker in full_text) >= 2:
        return f"Departure from {city}" if city else "Departure"

    if "tallin" in full_text or "tallinn" in full_text:
        if "old town" in full_text and "guided" in full_text and not any(marker in full_text for marker in ["helsinki", "ferry", "cruise", "star class", "port"]):
            return "Tallinn Old Town Guided Tour"
        return "Day Trip to Tallinn"

    if "fjellheisen" in full_text or ("round trip ticket" in full_text and "trom" in full_text) or "cable car" in full_text:
        return "Fjellheisen Cable Car"

    if "santa claus village" in full_text and ("reindeer" in full_text or "safari" in full_text):
        if "husky" in full_text:
            return "City Highlights, Santa Claus Village & Husky-Reindeer Safari"
        return "Santa Claus Village & Reindeer Visit"

    if "must-see bergen" in full_text or ("bergen" in full_text and "foot and boat" in full_text):
        return "Bergen Walking & Boat Tour"

    if "essential oslo" in full_text or ("oslo" in full_text and "city center guided walking tour" in full_text):
        return "Oslo City Center Walking Tour"

    if "guided walking tour of helsinki" in full_text or ("helsinki" in full_text and "guided walking tour" in full_text):
        return "Helsinki Guided Walking Tour"

    if "city walking" in full_text and "canal" in full_text and "copenhagen" in full_text:
        return "Copenhagen Walking & Canal Tour"

    if "optional addon" in full_text and any(marker in full_text for marker in ["svolvær", "svolvaer", "svolaver", "svoalvaer"]):
        return "Optional experience in Svolvær"

    if "lofoten" in full_text and "trollfjord" in full_text:
        return "Lofoten Day Tour & Trollfjord Cruise"

    if "guided city tour" in full_text and "narvik" in full_text:
        return "Narvik Guided City Tour"

    if "ice bar" in full_text and ("kiruna" in full_text or "jukkasjärvi" in full_text or "gällivare" in full_text or "gallivare" in full_text):
        return "Icehotel, Kiruna & Gällivare Touring Day"

    if "trom" in full_text and "city sightseeing" in full_text:
        if "aurora" in full_text or "northern light" in full_text:
            return "Tromsø City Sightseeing & Northern Lights Chase"
        return "Tromsø City Sightseeing"

    if "arctic wildlife" in full_text and "ranua" in full_text:
        return "Arctic Wildlife Adventure to Ranua Park"

    if "reindeer safari" in full_text and "santa" in full_text:
        return "Santa Claus Village & Reindeer Safari"

    if "fløibanen" in full_text or "floibanen" in full_text:
        return "Fløibanen Funicular"

    if "hop on" in full_text or "hop-on" in full_text or "hop off" in full_text or "hop-off" in full_text:
        if "copenhagen" in full_text:
            return "Copenhagen Hop-On Hop-Off Bus Ticket"
        if "bergen" in full_text:
            return "Bergen Hop-On Hop-Off Bus Ticket"
        return "Hop-On Hop-Off Bus Ticket"

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
        for word in ["hunt", "chase", "basecamp", "base camp", "cruise", "boat", "float", "floating", "mileage", "photo tour"]
    )

    is_northern_lights = title_has_northern_lights or (
        full_has_northern_lights and title_has_northern_lights_activity_word
    )

    if is_northern_lights:
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

    # Guardrail: never let long raw supplier prose become a title.
    clean = polish_title(title)
    if len(clean) > 90 or clean.count(".") >= 2:
        first = re.split(r"[.|]", clean, maxsplit=1)[0].strip(" ,-:")
        if first and len(first) <= 70:
            return polish_title(first)
        if city:
            return f"Guided experience in {city}"
        return "Guided experience"

    return clean

def create_trip_title(parsed_rows, grouped_days):
    parsed_rows = main_rows_only(parsed_rows)
    cities = get_unique_cities(parsed_rows)
    day_count = get_day_count(grouped_days)

    has_northern_lights = any(
        "northern light" in row.get("details", "").lower()
        or "aurora" in row.get("details", "").lower()
        for row in parsed_rows
    )

    has_lapland = any(
        city.lower() in ["rovaniemi", "levi", "saariselkä", "saariselka", "kittilä", "kittila", "kakslauttenen", "kakslauttanen", "ivalo"]
        for city in cities
    )

    if len(cities) == 1:
        city = cities[0]

        if has_northern_lights:
            return f"{city} Northern Lights Journey"

        return f"{city} City Break"

    if len(cities) == 2:
        if has_northern_lights or has_lapland:
            return f"{cities[0]} & {cities[1]} Arctic Journey"

        return f"{cities[0]} & {cities[1]} Nordic Journey"

    if has_northern_lights or has_lapland:
        return "Nordic Winter Journey"

    if day_count >= 10:
        return "Grand Nordic Journey"

    return "Nordic Discovery Journey"


def create_trip_subtitle(parsed_rows, grouped_days):
    parsed_rows = main_rows_only(parsed_rows)
    day_count = get_day_count(grouped_days)
    cities = get_unique_cities(parsed_rows)

    text = " ".join(row.get("details", "").lower() for row in parsed_rows)

    themes = []

    if "northern light" in text or "aurora" in text:
        themes.append("Northern Lights")

    if any(marker in text for marker in ["glass igloo", "kakslauttanen", "arctic resort"]):
        themes.append("Arctic Stays")

    if "fjord" in text:
        themes.append("Fjords")

    if "cruise" in text:
        themes.append("Coastal Cruises")

    if "train" in text or "rail" in text or "norway in a nutshell" in text:
        themes.append("Scenic Journeys")

    if "food" in text or "dinner" in text or "tasting" in text:
        themes.append("Local Food")

    if "walking tour" in text or "guide" in text or "guided" in text:
        themes.append("Guided Experiences")

    if not themes:
        themes.append("Culture")
        themes.append("Comfortable Travel")

    clean_themes = []
    for theme in themes:
        if theme not in clean_themes:
            clean_themes.append(theme)

    theme_text = ", ".join(clean_themes[:3])

    # When there are many destinations, avoid overcrowding the cover subtitle.
    if len(cities) >= 5:
        city_set = {city.lower() for city in cities}
        has_finland = any(city in city_set for city in ["helsinki", "rovaniemi", "ivalo", "kakslauttanen"])
        has_norway = any(city in city_set for city in ["tromsø", "tromso", "bergen", "oslo"])

        if has_finland and has_norway:
            return f"{day_count} Days Across Finland and Norway — {theme_text}"

        return f"{day_count} Days Across the Nordics — {theme_text}"

    if len(cities) > 1:
        destination_text = " · ".join(cities)
        return f"{day_count} Days Across {destination_text} — {theme_text}"

    if cities:
        return f"{day_count} Days in {cities[0]} — {theme_text}"

    return f"{day_count} Days — {theme_text}"

def create_destinations_line(parsed_rows):
    cities = get_unique_cities(parsed_rows)

    if not cities:
        return "Destinations will be detected from the itinerary text"

    return " · ".join(cities)


def create_trip_glance(parsed_rows, grouped_days):
    parsed_rows = main_rows_only(parsed_rows)
    cities = get_unique_cities(parsed_rows)
    day_count = get_day_count(grouped_days)
    nights = max(day_count - 1, 0)

    start_city = cities[0] if cities else "TBA"
    end_city = cities[-1] if cities else "TBA"
    destinations = " · ".join(cities) if cities else "TBA"

    hotel_rows = [row for row in parsed_rows if get_row_type(row) == "Hotel"]
    activity_rows = [row for row in parsed_rows if get_row_type(row) == "Activity"]
    transfer_rows = [row for row in parsed_rows if get_row_type(row) == "Transfer"]

    has_breakfast = any(
        "breakfast" in row.get("details", "").lower()
        or "brekafast" in row.get("details", "").lower()
        for row in hotel_rows
    )

    has_private_transfer = any(
        "private" in row.get("details", "").lower()
        for row in transfer_rows
    )

    has_self_transfer = any(
        "self transfer" in row.get("details", "").lower()
        for row in transfer_rows
    )

    travel_style_parts = []

    if has_private_transfer:
        travel_style_parts.append("private transfers")

    if has_self_transfer:
        travel_style_parts.append("self-guided transfers")

    if activity_rows:
        travel_style_parts.append("guided experiences")

    if hotel_rows:
        travel_style_parts.append("comfortable hotel stays")

    if travel_style_parts:
        travel_style = "Premium independent journey with " + ", ".join(travel_style_parts)
    else:
        travel_style = "Independent journey with arranged services"

    hotel_level = "Hotels as specified in the itinerary"

    if hotel_rows:
        hotel_level = "Accommodation as listed"

        if has_breakfast:
            hotel_level += ", breakfast included where specified"

    return {
        "Duration": f"{day_count} days / {nights} nights",
        "Start": start_city,
        "End": end_city,
        "Destinations": destinations,
        "Travel Style": travel_style,
        "Hotel Level": hotel_level,
    }


def describe_city_experience(rows):
    text = " ".join(row.get("details", "").lower() for row in rows)
    row_types = {get_row_type(row) for row in rows}
    cities = {str(row.get("city", "")).strip().lower() for row in rows if str(row.get("city", "")).strip()}

    if "bergen" in cities and "Hotel" in row_types and not any(get_row_type(row) == "Activity" for row in rows):
        return "Arrival in Bergen, overnight stay before the Norway in a Nutshell route"

    if has_glass_igloo_or_arctic_resort(rows):
        return "Arctic resort stay, glass igloo experience, remote Lapland scenery"

    if has_norway_in_a_nutshell(rows):
        return "Norway in a Nutshell route, scenic rail and fjord landscapes"

    if row_types == {"Hotel"}:
        return "Overnight stay and comfortable accommodation"

    if row_types.issubset({"Hotel", "Transfer"}) and any(get_row_type(row) == "Hotel" for row in rows):
        return "Arrival, overnight stay and comfortable accommodation"

    experiences = []

    if any(get_row_type(row) == "Arrival" for row in rows):
        experiences.append("arrival")

    if "walking tour" in text or "guided" in text or "guide" in text:
        experiences.append("guided sightseeing")

    if "northern light" in text or "aurora" in text:
        experiences.append("Northern Lights experiences")

    if "fjord" in text:
        experiences.append("fjord scenery")

    if "cruise" in text:
        experiences.append("coastal cruising")

    if "train" in text or "rail" in text:
        experiences.append("scenic rail travel")

    if "food" in text or "dinner" in text or "tasting" in text:
        experiences.append("local food culture")

    if any(get_row_type(row) == "Hotel" for row in rows):
        experiences.append("comfortable hotel stay")

    if not experiences:
        experiences.append("time to explore at your own pace")

    clean_experiences = []

    for experience in experiences:
        if experience not in clean_experiences:
            clean_experiences.append(experience)

    return ", ".join(clean_experiences[:4]).capitalize()

def create_journey_arc(grouped_days):
    chapters = []

    current_city = None
    current_days = []
    current_rows = []

    for day, rows in grouped_days.items():
        city = get_primary_city(rows)

        if not city:
            city = "Journey"

        if current_city is None:
            current_city = city
            current_days = [day]
            current_rows = list(rows)

        elif city == current_city:
            current_days.append(day)
            current_rows.extend(rows)

        else:
            chapters.append({
                "chapter": current_city,
                "days": format_day_range(current_days),
                "experience": describe_city_experience(current_rows),
            })

            current_city = city
            current_days = [day]
            current_rows = list(rows)

    if current_city is not None:
        chapters.append({
            "chapter": current_city,
            "days": format_day_range(current_days),
            "experience": describe_city_experience(current_rows),
        })

    return chapters


def format_day_range(days):
    if not days:
        return ""

    day_numbers = [get_day_number(day) for day in days]
    day_numbers = [number for number in day_numbers if number > 0]

    if not day_numbers:
        return "TBA"

    first_day = min(day_numbers)
    last_day = max(day_numbers)

    if first_day == last_day:
        return str(first_day)

    return f"{first_day} - {last_day}"


def create_day_title(day_rows):
    city = get_primary_city(day_rows)

    has_arrival = any(get_row_type(row) == "Arrival" for row in day_rows)
    has_departure = any(get_row_type(row) == "Departure" for row in day_rows)
    hotel_present = has_hotel(day_rows)
    transport_title = get_primary_transport_title(day_rows)
    activity_rows = [row for row in day_rows if get_row_type(row) == "Activity"]

    if has_only_departure_arrangements(day_rows) and city:
        return f"Departure from {city}"

    if has_arrival and city:
        return f"Welcome to {city}"

    # Travel days with a hotel check-in should be titled by the main travel
    # movement rather than by a later evening activity or transfer.
    if hotel_present and transport_title:
        return transport_title

    # Colleague format often starts with a transfer + hotel, without an explicit
    # Arrival row. Treat airport-to-hotel + accommodation as an arrival day only
    # when there is no separate flight/train/coach movement on the same day.
    if hotel_present and has_airport_arrival_transfer(day_rows) and city:
        return f"Welcome to {city}"

    if has_departure and city:
        return f"Departure from {city}"

    # If the day has an activity and later transport but no hotel check-in, let
    # the client-facing experience lead the day title.
    if activity_rows:
        title = create_client_activity_title(activity_rows[0])
        if title:
            return title

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

                if title:
                    return title

    return "Day at leisure"


def get_intro_variant_index(day_rows, variant_count=5):
    """Return a stable content-neutral variation index for day intro wording.

    The goal is to avoid repetitive client-facing prose without relying on
    specific dates, destinations, or itineraries. Day number gives stable
    variety while keeping regenerated output predictable.
    """
    if not day_rows or variant_count <= 0:
        return 0

    day_number = get_day_number(day_rows[0].get("day", ""))
    if day_number <= 0:
        return 0

    return (day_number - 1) % variant_count


def create_activity_intro_text(day_rows, activity_title, city_text, detail_level):
    """Create varied activity-day intro text without changing itinerary logic."""
    if detail_level == "Elegant concise":
        templates = [
            "Enjoy {activity_title} in {city_text}, with the rest of the day at your own pace.",
            "Spend part of the day on {activity_title} in {city_text}, with time left flexible.",
            "Experience {activity_title} in {city_text}, while keeping the day easy and balanced.",
            "Take in {activity_title} in {city_text}, with space around the experience for a relaxed pace.",
            "Your day includes {activity_title} in {city_text}, with free time around the main arrangement.",
        ]
    elif detail_level == "Rich descriptive":
        templates = [
            "The focus of the day is {activity_title} in {city_text}, adding a memorable highlight without making the itinerary feel overfilled.",
            "{activity_title} shapes the day in {city_text}, with time around the experience kept open so the schedule still feels easy and balanced.",
            "A key experience awaits in {city_text} with {activity_title}, while the rest of the day remains flexible for a comfortable pace.",
            "Your time in {city_text} continues with {activity_title}, paired with enough breathing room to enjoy the destination between arrangements.",
            "This day brings {activity_title} in {city_text}, giving the itinerary a strong local experience while still leaving space to explore at your own pace.",
        ]
    else:
        templates = [
            "Enjoy {activity_title} in {city_text}. The rest of the day can be shaped around your own pace, interests, and time at leisure.",
            "Spend part of the day on {activity_title} in {city_text}, with flexible time around the main experience.",
            "Experience {activity_title} in {city_text}, while keeping the overall pace clear and manageable.",
            "Take in {activity_title} in {city_text}, with the remaining time left open for a relaxed balance.",
            "Your day includes {activity_title} in {city_text}, with space around the arrangement for independent time.",
        ]

    template = templates[get_intro_variant_index(day_rows, len(templates))]
    return template.format(activity_title=activity_title, city_text=city_text)


def create_travel_intro_text(day_rows, city, detail_level):
    """Create varied travel-day intro text without changing page structure."""
    if detail_level == "Elegant concise":
        templates = [
            "Continue your journey with arranged travel connected to {city}.",
            "Travel onward to {city} with the key logistics arranged for you.",
            "Move on towards {city}, with the travel details kept clear and simple.",
            "This is a travel-led day towards {city}, with arrangements listed below.",
            "Continue to {city} through the arranged travel sequence for the day.",
        ]
    elif detail_level == "Rich descriptive":
        templates = [
            "The route continues towards {city}, with the day built around clear travel arrangements and a comfortable arrival into the next chapter.",
            "This is a travel-led day towards {city}, keeping the logistics straightforward while moving the journey smoothly onward.",
            "Your journey moves on to {city}, with the main travel pieces arranged in a clear sequence so the day feels easy to follow.",
            "Travel is the focus as you continue towards {city}, with the route structured to keep the transfer day calm and organised.",
            "The itinerary shifts towards {city}, bringing the next stage of the journey together through simple, well-organised travel arrangements.",
        ]
    else:
        templates = [
            "Today, you continue your journey with arranged travel connected to {city}. The day is structured to keep the route clear, comfortable, and easy to follow.",
            "Travel onward to {city}, with the main logistics arranged so the route remains clear and manageable.",
            "The journey continues towards {city}, with the day organised around the key travel arrangements listed below.",
            "This is a travel-focused day towards {city}, with each main movement kept simple and easy to follow.",
            "Continue to {city} through the arranged travel sequence for the day, keeping the next stage of the route straightforward.",
        ]

    template = templates[get_intro_variant_index(day_rows, len(templates))]
    return template.format(city=city)

def create_day_intro(day_rows, detail_level="Standard client itinerary"):
    """Create a client-facing day intro with adjustable detail level.

    Elegant concise keeps text short and practical.
    Standard client itinerary keeps the existing balanced style.
    Rich descriptive adds more atmosphere while staying client-facing.
    """

    detail_level = normalize_detail_level(detail_level)
    city = get_primary_city(day_rows)
    city_text = city or "the destination"

    has_arrival = any(get_row_type(row) == "Arrival" for row in day_rows)
    has_departure = any(get_row_type(row) == "Departure" for row in day_rows)

    activities = [row for row in day_rows if get_row_type(row) == "Activity"]
    transports = [row for row in day_rows if get_row_type(row) in TRANSPORT_TYPES]
    transfers = [row for row in day_rows if get_row_type(row) == "Transfer"]
    route_transfers = [row for row in transfers if is_route_transfer(row)]
    leisure = [row for row in day_rows if get_row_type(row) == "Leisure"]

    if has_only_departure_arrangements(day_rows) and city:
        transfer_title = get_first_transfer_title(day_rows).lower()
        if "self-guided" in transfer_title or "self transfer" in transfer_title:
            if detail_level == "Elegant concise":
                return f"After check-out, please make your own way to {city} Airport for your onward journey."
            return f"After check-out, please make your own way to {city} Airport for your onward journey."
        if detail_level == "Rich descriptive":
            return f"Your journey comes to a close today. After check-out, your arranged transfer will take you from your hotel to {city} Airport for your onward journey."
        return f"After check-out, your arranged transfer will take you from your hotel to {city} Airport for your onward journey."

    if has_arrival and city:
        if detail_level == "Elegant concise":
            return f"Welcome to {city}. Settle in and enjoy a smooth start to your journey."
        if detail_level == "Rich descriptive":
            return f"Welcome to {city}. After arrival, your arrangements are kept simple and comfortable, giving you time to settle in and ease into the first day of your journey."
        return (
            f"Welcome to {city}. After arrival, the day is designed to keep things "
            f"simple and comfortable as you settle into your accommodation."
        )

    if not transports and has_hotel(day_rows) and has_airport_arrival_transfer(day_rows) and city:
        if detail_level == "Elegant concise":
            return f"Welcome to {city}. Settle in and enjoy a smooth start to your stay."
        if detail_level == "Rich descriptive":
            return f"Welcome to {city}. Your arrival day is kept relaxed and comfortable, with time to settle into your accommodation and get your first feel for the destination."
        return (
            f"Welcome to {city}. After arrival, the day is designed to keep things "
            f"simple and comfortable as you settle into your accommodation."
        )

    if has_departure and city:
        if detail_level == "Elegant concise":
            return f"After check-out, your final arrangements in {city} are kept simple."
        if detail_level == "Rich descriptive":
            return f"After check-out, your final arrangements in {city} are kept smooth and straightforward, giving the journey an easy and well-organised finish."
        return f"After check-out, your final arrangements in {city} are kept simple and easy to follow."

    if activities:
        activity_title = get_client_activity_phrase(activities[0])
        activity_text = get_activity_text(activities[0])

        if "tallinn" in activity_text:
            if any(get_row_type(row) == "Train" and "overnight" in f'{row.get("title", "")} {row.get("details", "")}'.lower() for row in day_rows):
                if detail_level == "Elegant concise":
                    return "Enjoy a day trip from Helsinki to Tallinn before returning for your overnight train north."
                if detail_level == "Rich descriptive":
                    return "Today, you will cross from Helsinki to Tallinn for a memorable day trip, with time to experience the atmosphere of the historic Old Town before returning to Helsinki for your overnight train north."
                return (
                    "Today, you will enjoy a day trip from Helsinki to Tallinn, with time to explore "
                    "the Old Town before returning to Helsinki for your overnight train north."
                )
            if detail_level == "Elegant concise":
                return "Enjoy a day trip from Helsinki to Tallinn before returning for your onward journey."
            if detail_level == "Rich descriptive":
                return "Today, you will cross from Helsinki to Tallinn for a memorable day trip, with time to experience the historic Old Town before returning to Helsinki for your onward journey."
            return (
                "Today, you will enjoy a day trip from Helsinki to Tallinn, with time to explore "
                "the Old Town before returning to Helsinki for your onward journey."
            )

        if not has_hotel(day_rows) or not transports:
            return create_activity_intro_text(day_rows, activity_title, city_text, detail_level)

    if (transports or route_transfers) and city:
        travel_city = get_travel_destination_city(day_rows) or city
        return create_travel_intro_text(day_rows, travel_city, detail_level)

    if transfers and city:
        if detail_level == "Elegant concise":
            return f"Today’s arrangements in {city} are kept smooth and simple."
        if detail_level == "Rich descriptive":
            return f"Today’s arrangements in {city} are designed to keep the day smooth and comfortable, with the key logistics handled clearly."
        return (
            f"Today’s arrangements in {city} are designed to keep the journey smooth "
            f"and easy to follow."
        )

    if leisure and city:
        if detail_level == "Elegant concise":
            return f"Enjoy time at leisure in {city}."
        if detail_level == "Rich descriptive":
            return f"Enjoy a slower day in {city}, with time to explore independently, relax, or add optional experiences that suit your interests."
        return (
            f"Enjoy time at leisure in {city}. This is a good opportunity to explore "
            f"independently, relax, or add optional experiences."
        )

    if city:
        if detail_level == "Elegant concise":
            return f"Today is part of your stay in {city}, with arrangements listed below."
        if detail_level == "Rich descriptive":
            return f"Today is part of your stay in {city}, with the day’s arrangements laid out clearly so the experience feels relaxed and easy to follow."
        return (
            f"Today is part of your stay in {city}, with arrangements included as "
            f"listed below."
        )

    return "Today’s arrangements are listed below."


def sentence_case_transport_title(title):
    title = str(title or "").strip()
    replacements = {
        "Coach Transfer": "Coach transfer",
        "Tickets Included": "tickets included",
        "Tickets included": "tickets included",
        "Luggage porter service included": "luggage porter service",
    }
    for old, new in replacements.items():
        title = title.replace(old, new)
    return title


def clean_include_item(value, context_title=""):
    """Normalize inclusion bullet wording for both summaries and day blocks."""
    item = polish_inclusion_item(value, context_title)
    lower = item.lower()
    context_lower = str(context_title or "").lower()

    if lower in {"tickets included", "ticket included"}:
        if "coach" in context_lower or "bus" in context_lower:
            return "Coach ticket"
        if "train" in context_lower:
            return "Train ticket"
        if "ferry" in context_lower or "cruise" in context_lower:
            return "Ticket"
        return "Ticket"

    if lower == "luggage porter service included":
        return "Luggage porter service"

    if lower.endswith(" included") and len(item.split()) <= 5:
        # Keep complete sentence-style inclusions such as "Food and drinks are
        # included" or "Cookies are included". Stripping "included" there
        # creates broken bullets like "Food and drinks are".
        if re.search(r"\b(?:is|are)\s+included$", lower):
            return item
        return item[:-9].strip().capitalize()

    item = item.replace("Tickets included", "tickets included")
    item = item.replace("Luggage porter service included", "luggage porter service")
    item = item.replace("  ", " ")
    return polish_inclusion_item(item, context_title)


def format_transport_inclusion(title, includes=None, luggage=""):
    title = polish_title(sentence_case_transport_title(title))
    includes = [clean_include_item(item, title) for item in (includes or []) if clean_include_item(item, title)]
    luggage = clean_include_item(luggage, title)

    if luggage:
        return f"{title}, including {luggage}"

    if includes:
        include_text = ", ".join(includes)
        if len(includes) == 1 and "included" in include_text.lower():
            return f"{title}, {include_text}"
        return f"{title}, including {include_text}"

    return title


def create_whats_included(parsed_rows, grouped_days):
    parsed_rows = main_rows_only(parsed_rows)
    included = []

    hotel_rows = [row for row in parsed_rows if get_row_type(row) == "Hotel"]
    transfer_rows = [row for row in parsed_rows if get_row_type(row) == "Transfer"]
    transport_rows = [row for row in parsed_rows if get_row_type(row) in TRANSPORT_TYPES]
    activity_rows = [row for row in parsed_rows if get_row_type(row) == "Activity"]

    nights = max(get_day_count(grouped_days) - 1, 0)

    if hotel_rows:
        add_unique(included, f"{nights} nights as specified")
        add_unique(included, "Accommodation as listed in the itinerary")

    if any("breakfast" in row.get("details", "").lower() or "brekafast" in row.get("details", "").lower() for row in hotel_rows):
        add_unique(included, "Breakfast included where specified")

    has_private_transfer = any("private transfer" in row.get("details", "").lower() or "private" in row.get("title", "").lower() for row in transfer_rows)

    if has_private_transfer:
        add_unique(included, "Private transfers as listed in the itinerary")

    for row in transport_rows:
        if is_self_arranged(row):
            continue

        title = row.get("title", "").strip()
        luggage = row.get("luggage_included", "").strip()
        includes = row.get("includes", [])
        add_unique(included, format_transport_inclusion(title, includes, luggage))

    for row in transfer_rows:
        if is_route_transfer(row) and not is_self_arranged(row):
            add_unique(included, get_transfer_travel_title(row))

    for row in activity_rows:
        title = create_client_activity_title(row) or row.get("title", "").strip()

        if title:
            add_unique(included, title)

    return included

def create_whats_not_included():
    return [
        "International flights unless specifically listed",
        "Meals unless specifically stated",
        "Drinks unless specifically stated",
        "Porterage unless specified",
        "Self-guided transfers and self-arranged travel costs unless specifically stated",
        "Travel insurance",
        "Optional upgrades and personal expenses",
        "City taxes or local fees, where applicable",
    ]

def create_final_note(parsed_rows, grouped_days):
    # Kept for backward compatibility with older imports.
    return ""

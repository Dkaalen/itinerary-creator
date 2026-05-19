from collections import OrderedDict

from place_aliases import canonicalize_place_name, is_likely_service_text


TRANSPORT_TYPES = ["Transport", "Train", "Flight", "Cruise", "Ferry"]


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


def get_primary_transport_title(day_rows):
    for preferred_type in ["Flight", "Train", "Transport", "Cruise", "Ferry"]:
        for row in day_rows:
            if get_row_type(row) == preferred_type:
                title = str(row.get("title", "")).strip()
                if title:
                    return title
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


def create_client_activity_title(row):
    title = clean_client_title(row.get("title", ""))
    original_title = clean_client_title(row.get("original_title", "") or title)
    details = str(row.get("details", "") or "")

    title_text = f"{original_title} {title}".lower()
    full_text = f"{title_text} {details}".lower()

    if "tallinn" in full_text:
        return "Day Trip to Tallinn"

    if "optional addon" in full_text and any(marker in full_text for marker in ["svolvær", "svolvaer", "svolaver", "svoalvaer"]):
        return "Optional experience in Svolvær"

    if "lofoten" in full_text and "trollfjord" in full_text:
        return "Lofoten Day Tour & Trollfjord Cruise"

    if "fløibanen" in full_text or "floibanen" in full_text:
        return "Fløibanen Funicular"

    if "hop on" in full_text or "hop-on" in full_text or "hop off" in full_text or "hop-off" in full_text:
        if "copenhagen" in full_text:
            return "Copenhagen Hop-On Hop-Off Bus Ticket"
        if "bergen" in full_text:
            return "Bergen Hop-On Hop-Off Bus Ticket"
        return "Hop-On Hop-Off Bus Ticket"

    if "city walking" in full_text and "canal" in full_text and "copenhagen" in full_text:
        return "Copenhagen Walking & Canal Tour"

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

def create_day_intro(day_rows):
    city = get_primary_city(day_rows)

    has_arrival = any(get_row_type(row) == "Arrival" for row in day_rows)
    has_departure = any(get_row_type(row) == "Departure" for row in day_rows)

    activities = [row for row in day_rows if get_row_type(row) == "Activity"]
    transports = [row for row in day_rows if get_row_type(row) in TRANSPORT_TYPES]
    transfers = [row for row in day_rows if get_row_type(row) == "Transfer"]
    leisure = [row for row in day_rows if get_row_type(row) == "Leisure"]

    if has_only_departure_arrangements(day_rows) and city:
        transfer_title = get_first_transfer_title(day_rows).lower()
        if "self-guided" in transfer_title or "self transfer" in transfer_title:
            return f"After check-out, please make your own way to {city} Airport for your onward journey."
        return f"After check-out, your arranged transfer will take you from your hotel to {city} Airport for your onward journey."

    if has_arrival and city:
        return (
            f"Welcome to {city}. After arrival, the day is designed to keep things "
            f"simple and comfortable as you settle into your accommodation."
        )

    if not transports and has_hotel(day_rows) and has_airport_arrival_transfer(day_rows) and city:
        return (
            f"Welcome to {city}. After arrival, the day is designed to keep things "
            f"simple and comfortable as you settle into your accommodation."
        )

    if has_departure and city:
        return f"After check-out, your final arrangements in {city} are kept simple and easy to follow."

    if activities:
        activity_title = create_client_activity_title(activities[0]) or "your included experience"
        activity_text = get_activity_text(activities[0])

        if "tallinn" in activity_text:
            if any(get_row_type(row) == "Train" and "overnight" in f'{row.get("title", "")} {row.get("details", "")}'.lower() for row in day_rows):
                return (
                    "Today, you will enjoy a day trip from Helsinki to Tallinn, with time to explore "
                    "the Old Town before returning to Helsinki for your overnight train north."
                )
            return (
                "Today, you will enjoy a day trip from Helsinki to Tallinn, with time to explore "
                "the Old Town before returning to Helsinki for your onward journey."
            )

        # If this is mainly an activity day with late onward travel, keep the
        # intro focused on the experience rather than making it sound like a
        # generic transfer day.
        if not has_hotel(day_rows) or not transports:
            return (
                f"Today, you will enjoy {activity_title} in {city}. The rest of the day "
                f"can be shaped around your own pace, interests, and time at leisure."
            )

    if transports and city:
        return (
            f"Today, you continue your journey with arranged travel connected to {city}. "
            f"The day is structured to keep the route clear, comfortable, and easy to follow."
        )

    if transfers and city:
        return (
            f"Today’s arrangements in {city} are designed to keep the journey smooth "
            f"and easy to follow."
        )

    if leisure and city:
        return (
            f"Enjoy time at leisure in {city}. This is a good opportunity to explore "
            f"independently, relax, or add optional experiences."
        )

    if city:
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
    item = str(value or "").strip()
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
        return item[:-9].strip().capitalize()

    item = item.replace("Tickets included", "tickets included")
    item = item.replace("Luggage porter service included", "luggage porter service")
    item = item.replace("  ", " ")
    return item


def format_transport_inclusion(title, includes=None, luggage=""):
    title = sentence_case_transport_title(title)
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
        add_unique(included, f"{nights} nights / travel nights as specified")
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

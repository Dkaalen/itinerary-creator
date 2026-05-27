from itinerary_generation.common import (
    get_day_count,
    get_primary_city,
    get_row_type,
    get_unique_cities,
    clean_client_title,
    main_rows_only,
    has_hotel,
)
from itinerary_generation.transport import (
    get_primary_transport_title,
    has_airport_arrival_transfer,
    has_only_departure_arrangements,
)


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

    text = " ".join(row.get("details", "").lower() for row in parsed_rows)

    winter_markers = [
        "winter", "snow", "lapland", "rovaniemi", "saariselkä", "saariselka",
        "northern light", "aurora", "reindeer", "husky", "santa", "arctic",
        "glass igloo", "kakslauttanen",
    ]
    has_winter_focus = any(marker in text for marker in winter_markers)

    if has_winter_focus:
        return "A premium Nordic winter journey with scenic travel and Arctic experiences"

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

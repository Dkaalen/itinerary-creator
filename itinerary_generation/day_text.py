from itinerary_generation.common import (
    TRANSPORT_TYPES,
    get_activity_text,
    get_day_number,
    get_primary_city,
    get_row_type,
    has_hotel,
    normalize_detail_level,
)
from itinerary_generation.transport import (
    get_first_transfer_title,
    get_transfer_travel_title,
    has_airport_arrival_transfer,
    has_only_departure_arrangements,
    is_route_transfer,
)
from itinerary_generation.titles import create_client_activity_title


def get_client_activity_phrase(row):
    title = create_client_activity_title(row) or row.get("title", "your included experience")
    return title or "your included experience"


def _activity_phrase_with_city(activity_title, city_text):
    title = str(activity_title or "your included experience").strip()
    city = str(city_text or "").strip()
    if city and city.lower() in title.lower():
        return title
    return f"{title} in {city}" if city else title


def _canonical_route_city(name):
    clean = str(name or "").strip()
    replacements = {
        "saariselka": "Saariselkä",
        "kakslauttenen": "Kakslauttanen",
        "tromso": "Tromsø",
    }
    return replacements.get(clean.lower(), clean)


ROUTE_CITY_CANDIDATES = [
    "Helsinki", "Rovaniemi", "Saariselkä", "Saariselka",
    "Kakslauttanen", "Kakslauttenen", "Ivalo",
    "Oslo", "Bergen", "Copenhagen", "Stockholm", "Tromsø", "Tromso",
]


def _ordered_route_cities(day_rows):
    cities = []

    def add_city(city):
        city = _canonical_route_city(city)
        if city and city.lower() not in [existing.lower() for existing in cities]:
            cities.append(city)

    for row in day_rows:
        if get_row_type(row) not in TRANSPORT_TYPES and get_row_type(row) != "Transfer" and not is_route_transfer(row):
            continue
        add_city(row.get("city", ""))
        row_text = get_transfer_travel_title(row) if is_route_transfer(row) else f'{row.get("title", "")} {row.get("details", "")}'
        for possible_city in ROUTE_CITY_CANDIDATES:
            if possible_city.lower() in row_text.lower():
                add_city(possible_city)
    return cities


def create_travel_route_label(day_rows):
    """Return a natural route label for travel-only days, when clear enough."""

    has_activity_or_hotel = any(get_row_type(row) in {"Activity", "Hotel"} for row in day_rows)
    if has_activity_or_hotel:
        return ""

    travel_rows = [row for row in day_rows if get_row_type(row) in TRANSPORT_TYPES or get_row_type(row) == "Transfer" or is_route_transfer(row)]
    if len(travel_rows) < 2:
        return ""

    cities = _ordered_route_cities(day_rows)
    if len(cities) < 3:
        return ""

    has_overnight_final_leg = any(
        "overnight" in f'{row.get("title", "")} {row.get("details", "")}'.lower()
        for row in travel_rows[-1:]
    )
    if has_overnight_final_leg:
        return f"{cities[0]} to {cities[-2]}, overnight to {cities[-1]}"

    return f"{cities[0]} to {cities[-1]}"


def create_day_intro(day_rows, detail_level="Standard client itinerary"):
    """Create a premium, client-facing day intro.

    This function is intentionally deterministic and pattern-based. It avoids
    the repeated "Today, you will enjoy..." wording that made longer itineraries
    feel templated, while keeping arrival, departure, travel and activity-led
    days clear for any similar supplier input structure.
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
        has_transfer_row = any(get_row_type(row) == "Transfer" for row in day_rows)
        if not has_transfer_row:
            if detail_level == "Rich descriptive":
                return f"Your journey comes to a close in {city} today, with time for check-out before you continue your travels home."
            return f"Your journey comes to a close in {city} today before your journey home."
        if "self-guided" in transfer_title or "self transfer" in transfer_title:
            return f"After check-out, please make your own way to {city} Airport for your onward journey."
        if detail_level == "Rich descriptive":
            return f"Your journey comes to a close today. After check-out, your arranged transfer will take you from your hotel to {city} Airport for your onward journey."
        return f"After check-out, your arranged transfer will take you from your hotel to {city} Airport for your onward journey."

    if has_arrival and city:
        if detail_level == "Elegant concise":
            return f"Welcome to {city}. Settle in and enjoy a smooth start to your journey."
        if detail_level == "Rich descriptive":
            return f"Welcome to {city}. Your arrival day is kept relaxed and comfortable, with time to settle into your accommodation and get your first feel for the destination."
        return f"Welcome to {city}. The day is kept simple and comfortable as you settle into your accommodation."

    if not transports and has_hotel(day_rows) and has_airport_arrival_transfer(day_rows) and city:
        if detail_level == "Elegant concise":
            return f"Welcome to {city}. Settle in and enjoy a smooth start to your stay."
        if detail_level == "Rich descriptive":
            return f"Welcome to {city}. Your arrival day is kept relaxed and comfortable, with time to settle into your accommodation and get your first feel for the destination."
        return f"Welcome to {city}. The day is kept simple and comfortable as you settle into your accommodation."

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
                    return "Cross from Helsinki to Tallinn for a memorable day trip, with time to experience the atmosphere of the historic Old Town before returning to Helsinki for your overnight train north."
                return "Enjoy a day trip from Helsinki to Tallinn, with time to explore the Old Town before returning to Helsinki for your overnight train north."
            if detail_level == "Elegant concise":
                return "Enjoy a day trip from Helsinki to Tallinn before returning for your onward journey."
            if detail_level == "Rich descriptive":
                return "Cross from Helsinki to Tallinn for a memorable day trip, with time to experience the historic Old Town before returning to Helsinki for your onward journey."
            return "Enjoy a day trip from Helsinki to Tallinn, with time to explore the Old Town before returning to Helsinki for your onward journey."

        if not has_hotel(day_rows) or not transports:
            if detail_level == "Elegant concise":
                return f"{activity_title} is the main arranged experience in {city_text}, with the rest of the day kept flexible."

            activity_with_city = _activity_phrase_with_city(activity_title, city_text)
            intro_variants = [
                (
                    f"{activity_title} gives the day a clear focus in {city_text}, "
                    f"with time around the experience kept open and comfortable."
                ),
                (
                    f"The day is shaped around {activity_with_city}, "
                    f"balanced with space to enjoy the destination at an easy pace."
                ),
                (
                    f"A planned highlight brings you into {activity_with_city}, "
                    f"while the rest of the schedule remains relaxed and simple."
                ),
                (
                    f"Your main experience today is {activity_title}, offering a well-paced "
                    f"way to enjoy {city_text} without overfilling the day."
                ),
            ]
            variant_index = (get_day_number(day_rows[0].get("day", "")) - 1) % len(intro_variants)
            return intro_variants[variant_index]

    if (transports or route_transfers) and city:
        route_label = create_travel_route_label(day_rows)
        if route_label:
            if detail_level == "Elegant concise":
                return f"Continue your journey from {route_label}."
            if detail_level == "Rich descriptive":
                return f"The journey continues from {route_label}, with the travel arrangements structured to keep the route clear, comfortable, and easy to follow."
            return f"Continue your journey from {route_label}. The route is structured to stay clear, comfortable, and easy to follow."

        destination_city = ""
        travel_rows = [row for row in day_rows if get_row_type(row) in TRANSPORT_TYPES or get_row_type(row) == "Transfer" or is_route_transfer(row)]
        for row in travel_rows:
            row_text = get_transfer_travel_title(row) if is_route_transfer(row) else f'{row.get("title", "")} {row.get("details", "")}'
            for possible_city in ROUTE_CITY_CANDIDATES:
                if possible_city.lower() in row_text.lower():
                    destination_city = _canonical_route_city(possible_city)
        display_city = destination_city or city
        if detail_level == "Elegant concise":
            return f"Continue your journey with arranged travel connected to {display_city}."
        if detail_level == "Rich descriptive":
            return f"The journey continues towards {display_city}, with the travel arrangements structured to keep the route clear, comfortable, and easy to follow."
        return f"Continue your journey with arranged travel connected to {display_city}. The route is structured to stay clear, comfortable, and easy to follow."

    if transfers and city:
        if detail_level == "Elegant concise":
            return f"Arrangements in {city} are kept smooth and simple."
        if detail_level == "Rich descriptive":
            return f"The arrangements in {city} are designed to keep the day smooth and comfortable, with the key logistics handled clearly."
        return f"Arrangements in {city} are designed to keep the journey smooth and easy to follow."

    if leisure and city:
        if detail_level == "Elegant concise":
            return f"Enjoy time at leisure in {city}."
        if detail_level == "Rich descriptive":
            return f"Enjoy a slower day in {city}, with time to explore independently, relax, or add optional experiences that suit your interests."
        return f"Enjoy time at leisure in {city}. This is a good opportunity to explore independently, relax, or add optional experiences."

    if city:
        if detail_level == "Elegant concise":
            return f"This is part of your stay in {city}, with arrangements listed below."
        if detail_level == "Rich descriptive":
            return f"This is part of your stay in {city}, with the day’s arrangements laid out clearly so the experience feels relaxed and easy to follow."
        return f"This is part of your stay in {city}, with arrangements included as listed below."

    return "The day’s arrangements are listed below."

import re

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
    get_route_points_for_transport,
    has_airport_arrival_transfer,
    has_only_departure_arrangements,
    is_route_transfer,
)
from itinerary_generation.titles import create_client_activity_title, normalize_client_day_title
from parser_modules.common import extract_route_points
from place_aliases import country_for_place


def get_client_activity_phrase(row):
    title = create_client_activity_title(row) or row.get("title", "your included experience")
    return normalize_client_day_title(title, row) or title or "your included experience"


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
        "svolvaer": "Svolvær",
        "svolaver": "Svolvær",
        "gothernburg": "Gothenburg",
        "göteborg": "Gothenburg",
        "malmo": "Malmø",
    }
    return replacements.get(clean.lower(), clean)


ROUTE_CITY_CANDIDATES = [
    "Helsinki", "Rovaniemi", "Saariselkä", "Saariselka",
    "Kakslauttanen", "Kakslauttenen", "Ivalo",
    "Oslo", "Bergen", "Copenhagen", "Stockholm", "Tromsø", "Tromso", "Svolvær", "Svolvaer", "Svolaver", "Gothenburg", "Göteborg", "Malmo", "Malmø", "Alta", "Kirkenes",
]


def _arrival_display_destination(city):
    """Use a warm destination label for arrival intros."""
    country = country_for_place(city)
    if country == "Iceland":
        return "Iceland"
    return city or "the destination"


def _arrival_transfer_phrase(day_rows):
    for row in day_rows:
        if get_row_type(row) != "Transfer":
            continue
        title = get_first_transfer_title([row]) or row.get("title", "")
        lower = str(title).lower()
        if "self" in lower:
            return "After arrival, make your own way to your accommodation."
        if "flybus" in lower or "shuttle" in lower:
            return "On arrival, your arranged Flybus transfer will take you from the airport towards your accommodation area."
        if "private" in lower or "transfer" in lower:
            return "On arrival, your arranged transfer will take you from the airport to your accommodation."
    return "On arrival, make your way to your accommodation and check in."


def _is_group_tour_overview(row):
    text = f'{row.get("title", "")} {row.get("details", "")} {row.get("original_title", "")}'.lower()
    return get_row_type(row) == "Day Overview" and any(marker in text for marker in ["group tour", "holiday package", "sharing room basis"])


def _format_group_tour_pickup_range(hour, minute, suffix):
    start = f"{hour}:{minute} {suffix}"
    try:
        end_minute = int(minute) + 30
        end_hour = int(hour) + (1 if end_minute >= 60 else 0)
        end_minute = end_minute % 60
        if suffix == "PM" and end_hour > 12:
            end_hour -= 12
        return f"between {start} and {end_hour}:{end_minute:02d} {suffix}"
    except Exception:
        return f"at {start}"


def _extract_group_tour_overview_start_time(day_rows):
    for row in day_rows:
        if not _is_group_tour_overview(row):
            continue
        text = f'{row.get("title", "")} | {row.get("details", "")} | {row.get("original_title", "")}'
        match = re.search(r"\|\s*(\d{1,2})(?::(\d{2}))?\s*([AaPp]\.?[Mm]\.?)\b", text)
        if match:
            hour = int(match.group(1))
            minute = match.group(2) or "00"
            suffix = match.group(3).replace(".", "").upper()
            return _format_group_tour_pickup_range(hour, minute, suffix)
    return ""


def _is_group_tour_start_day(day_rows):
    return any(_is_group_tour_overview(row) for row in day_rows) and any(get_row_type(row) == "Activity" for row in day_rows)


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

    if _is_group_tour_start_day(day_rows):
        activity_title = get_client_activity_phrase(activities[0]) if activities else "the first included experience"
        start_time = _extract_group_tour_overview_start_time(day_rows)
        if start_time:
            pickup_sentence = f"Pick-up is scheduled {start_time} before you travel with your guide into {city_text}."
        else:
            pickup_sentence = f"After morning pick-up, travel with your guide into {city_text}."
        return (
            f"Your guided group tour begins today. {pickup_sentence} "
            f"Today introduces {activity_title}, setting the tone for the journey ahead."
        )

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
        destination = _arrival_display_destination(city)
        transfer_phrase = _arrival_transfer_phrase(day_rows)
        if detail_level == "Elegant concise":
            return f"Welcome to {destination}. {transfer_phrase}"
        if detail_level == "Rich descriptive":
            return f"Welcome to {destination}. {transfer_phrase} After check-in, the rest of the day is yours to settle in, relax, and enjoy your first impression of the destination."
        return f"Welcome to {destination}. {transfer_phrase} After check-in, enjoy time to settle in."

    if not transports and has_hotel(day_rows) and has_airport_arrival_transfer(day_rows) and city:
        destination = _arrival_display_destination(city)
        transfer_phrase = _arrival_transfer_phrase(day_rows)
        if detail_level == "Elegant concise":
            return f"Welcome to {destination}. {transfer_phrase}"
        if detail_level == "Rich descriptive":
            return f"Welcome to {destination}. {transfer_phrase} After check-in, the rest of the day is yours to settle in, relax, and enjoy your first impression of the destination."
        return f"Welcome to {destination}. {transfer_phrase} After check-in, enjoy time to settle in."

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

            activity_city = str(activities[0].get("city", "") or "").strip()
            city_for_activity = city_text
            if activity_city and city_text and activity_city.lower() != city_text.lower():
                city_for_activity = ""
            activity_with_city = _activity_phrase_with_city(activity_title, city_for_activity)
            destination_wording = city_text if city_for_activity else "the day"
            clear_focus_phrase = (
                f"{activity_title} gives the day a clear focus in {city_text}, "
                f"with time around the experience kept open and comfortable."
            ) if city_for_activity else (
                f"{activity_title} sets the tone for the day, "
                f"with the wider arrangements kept clear and comfortable."
            )
            intro_variants = [
                clear_focus_phrase,
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
                    f"way to enjoy the experience without overfilling the day."
                ),
            ]
            variant_index = (get_day_number(day_rows[0].get("day", "")) - 1) % len(intro_variants)
            return intro_variants[variant_index]

    if (transports or route_transfers) and city:
        transport_context = " ".join(f'{row.get("title", "")} {row.get("details", "")} {row.get("original_title", "")}' for row in transports + route_transfers).lower()
        if ("norway in a nutshell" in transport_context or "nærøyfjord" in transport_context or "naeroyfjord" in transport_context or "flåm train" in transport_context or "flam train" in transport_context):
            if detail_level == "Rich descriptive":
                return f"The journey continues towards {city}, with the Norway in a Nutshell route arranged as a clear and scenic travel day."
            return f"Continue your Norway in a Nutshell journey towards {city}."

        route_label = create_travel_route_label(day_rows)
        if route_label:
            if detail_level == "Elegant concise":
                return f"Continue your journey from {route_label}."
            if detail_level == "Rich descriptive":
                return f"The journey continues from {route_label}, with the travel arrangements structured to keep the route clear, comfortable, and easy to follow."
            return f"Continue your journey from {route_label}. The route is structured to stay clear, comfortable, and easy to follow."

        destination_city = ""
        invalid_destination_words = {"hotel", "station", "airport", "accommodation", "your accommodation", "self transfer", "private airport to hotel", "private hotel to airport"}
        travel_rows = [row for row in day_rows if get_row_type(row) in TRANSPORT_TYPES or get_row_type(row) == "Transfer" or is_route_transfer(row)]
        for row in travel_rows:
            origin, route_destination = get_route_points_for_transport(row) if get_row_type(row) in TRANSPORT_TYPES else ("", "")
            if not route_destination and is_route_transfer(row):
                _, route_destination = extract_route_points(get_transfer_travel_title(row))
            candidate = str(route_destination or "").strip()
            lower_candidate = candidate.lower()
            if candidate and lower_candidate not in invalid_destination_words and not any(bad in lower_candidate for bad in ["shower", "sink", "wc", "benefits", "made bed"]):
                destination_city = _canonical_route_city(candidate)
                continue
            title_match = re.search(r"\bto\s+([A-Za-zÀ-ÿøØåÅäÄöÖ]+(?:\s+[A-Za-zÀ-ÿøØåÅäÄöÖ]+)?)\s*$", str(row.get("title", "")), flags=re.IGNORECASE)
            if title_match and title_match.group(1).lower() not in invalid_destination_words:
                destination_city = _canonical_route_city(title_match.group(1))
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

from collections import OrderedDict


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


def get_unique_cities(parsed_rows):
    cities = []

    for row in parsed_rows:
        city = row.get("city", "").strip()

        if city and city not in cities:
            cities.append(city)

    return cities


def get_primary_city(day_rows):
    """
    Prefer the destination/stay city for mixed transfer days.
    This prevents days such as Tromsø -> Bergen from showing only Tromsø.
    """

    if not day_rows:
        return ""

    priority_types = [
        "Hotel",
        "Activity",
        "Arrival",
        "Departure",
        "Flight",
        "Train",
        "Cruise",
        "Ferry",
        "Transfer",
    ]

    for preferred_type in priority_types:
        for row in day_rows:
            if get_row_type(row) == preferred_type:
                city = row.get("city", "").strip()
                if city:
                    return city

    return day_rows[0].get("city", "").strip()


def create_trip_title(parsed_rows, grouped_days):
    cities = get_unique_cities(parsed_rows)
    day_count = get_day_count(grouped_days)

    has_northern_lights = any(
        "northern light" in row.get("details", "").lower()
        or "aurora" in row.get("details", "").lower()
        for row in parsed_rows
    )

    has_lapland = any(
        city.lower() in ["rovaniemi", "levi", "saariselkä", "saariselka", "kittilä", "kittila"]
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
    day_count = get_day_count(grouped_days)
    cities = get_unique_cities(parsed_rows)

    text = " ".join(row.get("details", "").lower() for row in parsed_rows)

    themes = []

    if "northern light" in text or "aurora" in text:
        themes.append("Northern Lights")

    if "fjord" in text:
        themes.append("Fjords")

    if "cruise" in text:
        themes.append("Coastal Cruises")

    if "train" in text or "rail" in text:
        themes.append("Scenic Rail")

    if "food" in text or "dinner" in text or "tasting" in text:
        themes.append("Local Food")

    if "walking tour" in text or "guide" in text or "guided" in text:
        themes.append("Guided Experiences")

    if not themes:
        themes.append("Culture")
        themes.append("Comfortable Travel")

    theme_text = ", ".join(themes[:3])

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
        "breakfast included" in row.get("details", "").lower()
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

    if has_arrival and city:
        return f"Welcome to {city}"

    if has_departure and city:
        return f"Final day in {city}"

    priority_order = [
        "Activity",
        "Transport",
        "Train",
        "Flight",
        "Cruise",
        "Ferry",
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

    if has_arrival and city:
        return (
            f"Welcome to {city}. After arrival, the day is designed to keep things "
            f"simple and comfortable as you settle into your accommodation."
        )

    if has_departure and city:
        return (
            f"Your journey comes to a close in {city}. The practical details below "
            f"help keep the final day clear and easy to follow."
        )

    if transports and city:
        return (
            f"Today, you continue your journey with arranged travel connected to {city}. "
            f"The day is structured to keep the route clear, comfortable, and easy to follow."
        )

    if activities and city:
        activity_title = activities[0].get("title", "your included experience")

        return (
            f"Today, you will enjoy {activity_title} in {city}. The rest of the day "
            f"can be shaped around your own pace, interests, and time at leisure."
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


def create_whats_included(parsed_rows, grouped_days):
    included = []

    hotel_rows = [row for row in parsed_rows if get_row_type(row) == "Hotel"]
    transfer_rows = [row for row in parsed_rows if get_row_type(row) == "Transfer"]
    transport_rows = [row for row in parsed_rows if get_row_type(row) in TRANSPORT_TYPES]
    activity_rows = [row for row in parsed_rows if get_row_type(row) == "Activity"]

    nights = max(get_day_count(grouped_days) - 1, 0)

    if hotel_rows:
        add_unique(included, f"{nights} nights / travel nights as specified")
        add_unique(included, "Accommodation as listed in the itinerary")

    if any("breakfast included" in row.get("details", "").lower() for row in hotel_rows):
        add_unique(included, "Breakfast included where specified")

    has_private_transfer = any("private transfer" in row.get("details", "").lower() for row in transfer_rows)

    if has_private_transfer:
        add_unique(included, "Private transfers as listed in the itinerary")

    for row in transport_rows:
        title = row.get("title", "").strip()
        luggage = row.get("luggage_included", "").strip()
        includes = row.get("includes", [])

        if luggage:
            add_unique(included, f"{title}, including {luggage}")
        elif includes:
            add_unique(included, f"{title} with {', '.join(includes)}")
        else:
            add_unique(included, title)

    for row in activity_rows:
        title = row.get("title", "").strip()

        if title:
            add_unique(included, title)

    return included


def create_whats_not_included(parsed_rows):
    return [
        "International flights unless specifically listed",
        "Meals unless specifically stated",
        "Drinks unless specifically stated",
        "Porterage unless specified",
        "Self-guided transfer costs unless specifically stated",
        "Travel insurance",
        "Optional upgrades and personal expenses",
        "City taxes or local fees, where applicable",
    ]


def create_final_note(parsed_rows, grouped_days):
    # Kept for backward compatibility with older imports.
    return ""

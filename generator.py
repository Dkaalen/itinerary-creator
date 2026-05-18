from collections import defaultdict


def group_rows_by_day(parsed_rows):
    """
    Groups parsed itinerary rows by day.
    Example:
    Day 1 -> Arrival, Transfer, Hotel
    Day 2 -> Activity
    """

    grouped = defaultdict(list)

    for row in parsed_rows:
        day = row.get("day", "Unknown day")
        grouped[day].append(row)

    return dict(grouped)


def get_unique_cities(parsed_rows):
    """
    Returns unique cities in the order they appear.
    """

    cities = []

    for row in parsed_rows:
        city = row.get("city", "").strip()

        if city and city not in cities:
            cities.append(city)

    return cities


def get_day_count(grouped_days):
    """
    Counts the number of itinerary days.
    """

    return len(grouped_days)


def create_trip_title(parsed_rows, grouped_days):
    """
    Creates a polished trip title automatically from the itinerary text.
    """

    cities = get_unique_cities(parsed_rows)
    day_count = get_day_count(grouped_days)

    has_northern_lights = any(
        "northern light" in row.get("details", "").lower()
        or "aurora" in row.get("details", "").lower()
        for row in parsed_rows
    )

    has_fjord = any(
        "fjord" in row.get("details", "").lower()
        for row in parsed_rows
    )

    has_iceland = any(
        city.lower() in ["reykjavik", "keflavik"]
        for city in cities
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

    if has_iceland and has_fjord:
        return "Nordic Fjords & Iceland Journey"

    if has_northern_lights or has_lapland:
        return "Nordic Winter Journey"

    if day_count >= 10:
        return "Grand Nordic Journey"

    return "Nordic Discovery Journey"


def create_trip_subtitle(parsed_rows, grouped_days):
    """
    Creates a subtitle that complements the generated title.
    """

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

    if "blue lagoon" in text or "glacier" in text or "waterfall" in text:
        themes.append("Icelandic Landscapes")

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
    """
    Creates the destination line shown on the cover page.
    """

    cities = get_unique_cities(parsed_rows)

    if not cities:
        return "Destinations will be detected from the itinerary text"

    return " · ".join(cities)


def create_trip_glance(parsed_rows, grouped_days):
    """
    Creates automatic Trip at a Glance information.
    """

    cities = get_unique_cities(parsed_rows)
    day_count = get_day_count(grouped_days)

    nights = max(day_count - 1, 0)

    start_city = cities[0] if cities else "TBA"
    end_city = cities[-1] if cities else "TBA"
    destinations = " · ".join(cities) if cities else "TBA"

    hotel_rows = [row for row in parsed_rows if row.get("type") == "Hotel"]
    activity_rows = [row for row in parsed_rows if row.get("type") == "Activity"]
    transfer_rows = [row for row in parsed_rows if row.get("type") == "Transfer"]

    has_breakfast = any(
        "breakfast included" in row.get("details", "").lower()
        for row in hotel_rows
    )

    has_private_transfer = any(
        "private" in row.get("details", "").lower()
        for row in transfer_rows
    )

    travel_style_parts = []

    if has_private_transfer:
        travel_style_parts.append("private transfers")

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


def create_day_title(day_rows):
    """
    Creates a clean day title based on the most important row.
    Arrival and departure days get special title logic.
    """

    city = day_rows[0].get("city", "").strip() if day_rows else ""

    has_arrival = any(row.get("type") == "Arrival" for row in day_rows)
    has_departure = any(row.get("type") == "Departure" for row in day_rows)

    if has_arrival and city:
        return f"Welcome to {city}"

    if has_departure and city:
        return f"Departure from {city}"

    priority_order = ["Activity", "Transfer", "Hotel", "Leisure"]

    for item_type in priority_order:
        for row in day_rows:
            if row.get("type") == item_type:
                title = row.get("title", "").strip()
                if title:
                    return title

    return "Day at leisure"


def create_day_intro(day_rows):
    """
    Creates a short intro paragraph for each day.
    This is still simple, but gives the itinerary a more polished feel.
    """

    city = day_rows[0].get("city", "").strip() if day_rows else ""

    has_arrival = any(row.get("type") == "Arrival" for row in day_rows)
    has_departure = any(row.get("type") == "Departure" for row in day_rows)
    has_hotel = any(row.get("type") == "Hotel" for row in day_rows)
    activities = [row for row in day_rows if row.get("type") == "Activity"]
    transfers = [row for row in day_rows if row.get("type") == "Transfer"]
    leisure = [row for row in day_rows if row.get("type") == "Leisure"]

    if has_arrival and city:
        return (
            f"Welcome to {city}. After arrival, the day is designed to keep things "
            f"simple and comfortable as you settle into your accommodation."
        )

    if has_departure and city:
        return (
            f"Your journey comes to an end in {city}. Today is focused on your "
            f"departure arrangements and your onward travel."
        )

    if activities and city:
        activity_title = activities[0].get("title", "your included experience")
        return (
            f"Today, you will enjoy {activity_title} in {city}. The rest of the day "
            f"can be shaped around your own pace, interests, and time at leisure."
        )

    if transfers and has_hotel and city:
        return (
            f"Today, you continue your journey to {city}. Transfers and accommodation "
            f"are arranged to keep the travel day smooth and comfortable."
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
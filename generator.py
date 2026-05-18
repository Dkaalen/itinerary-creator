from collections import OrderedDict

APP_FIX_VERSION = "2026-05-18 v5 activity-inclusions-no-final-note"

TRANSPORT_TYPES = ["Transport", "Train", "Flight", "Cruise", "Ferry"]
DAY_PRIORITY_TYPES = ["Activity", "Flight", "Train", "Cruise", "Ferry", "Transport", "Transfer", "Hotel", "Leisure"]


def get_row_type(row):
    return row.get("effective_type") or row.get("type", "")


def get_day_number(day_text):
    digits = "".join(ch for ch in str(day_text) if ch.isdigit())
    return int(digits) if digits else 0


def group_rows_by_day(parsed_rows):
    grouped = OrderedDict()
    for row in parsed_rows:
        day = row.get("day", "").strip() or "Unknown day"
        grouped.setdefault(day, []).append(row)
    return OrderedDict(sorted(grouped.items(), key=lambda item: get_day_number(item[0])))


def add_unique(items, item):
    clean_item = (item or "").strip()
    if clean_item and clean_item not in items:
        items.append(clean_item)


def get_unique_cities(parsed_rows):
    cities = []
    for row in parsed_rows:
        city = row.get("city", "").strip()
        if city and city not in cities:
            cities.append(city)
    return cities


def get_day_count(grouped_days):
    return len(grouped_days)


def get_primary_city(day_rows):
    if not day_rows:
        return ""

    # For travel days, prefer the destination city where the client ends/sleeps.
    for preferred_type in ["Hotel", "Activity", "Arrival", "Departure"]:
        for row in day_rows:
            if get_row_type(row) == preferred_type and row.get("city", "").strip():
                return row.get("city", "").strip()

    for row in reversed(day_rows):
        city = row.get("city", "").strip()
        if city:
            return city
    return ""


def create_trip_title(parsed_rows, grouped_days):
    cities = get_unique_cities(parsed_rows)
    day_count = get_day_count(grouped_days)
    text = " ".join(row.get("details", "").lower() for row in parsed_rows)
    has_northern_lights = "northern light" in text or "aurora" in text
    has_lapland = any(city.lower() in ["rovaniemi", "levi", "saariselkä", "saariselka", "kittilä", "kittila"] for city in cities)

    if len(cities) == 1:
        return f"{cities[0]} Northern Lights Journey" if has_northern_lights else f"{cities[0]} City Break"
    if len(cities) == 2:
        return f"{cities[0]} & {cities[1]} Arctic Journey" if (has_northern_lights or has_lapland) else f"{cities[0]} & {cities[1]} Nordic Journey"
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
        themes = ["Culture", "Comfortable Travel"]
    theme_text = ", ".join(themes[:3])
    if len(cities) > 1:
        return f"{day_count} Days Across {' · '.join(cities)} — {theme_text}"
    if cities:
        return f"{day_count} Days in {cities[0]} — {theme_text}"
    return f"{day_count} Days — {theme_text}"


def create_destinations_line(parsed_rows):
    cities = get_unique_cities(parsed_rows)
    return " · ".join(cities) if cities else "Destinations will be detected from the itinerary text"


def create_trip_glance(parsed_rows, grouped_days):
    cities = get_unique_cities(parsed_rows)
    day_count = get_day_count(grouped_days)
    nights = max(day_count - 1, 0)
    hotel_rows = [row for row in parsed_rows if get_row_type(row) == "Hotel"]
    activity_rows = [row for row in parsed_rows if get_row_type(row) == "Activity"]
    transfer_rows = [row for row in parsed_rows if get_row_type(row) == "Transfer"]
    has_breakfast = any("breakfast included" in row.get("details", "").lower() for row in hotel_rows)
    has_private_transfer = any("private" in row.get("details", "").lower() for row in transfer_rows)
    has_self_transfer = any("self transfer" in row.get("details", "").lower() for row in transfer_rows)
    travel_style_parts = []
    if has_private_transfer:
        travel_style_parts.append("private transfers")
    if has_self_transfer:
        travel_style_parts.append("self-guided transfers")
    if activity_rows:
        travel_style_parts.append("guided experiences")
    if hotel_rows:
        travel_style_parts.append("comfortable hotel stays")
    return {
        "Duration": f"{day_count} days / {nights} nights",
        "Start": cities[0] if cities else "TBA",
        "End": cities[-1] if cities else "TBA",
        "Destinations": " · ".join(cities) if cities else "TBA",
        "Travel Style": "Premium independent journey with " + ", ".join(travel_style_parts) if travel_style_parts else "Independent journey with arranged services",
        "Hotel Level": "Accommodation as listed, breakfast included where specified" if hotel_rows and has_breakfast else ("Accommodation as listed" if hotel_rows else "Hotels as specified in the itinerary"),
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
    clean = []
    for exp in experiences:
        if exp not in clean:
            clean.append(exp)
    return ", ".join(clean[:4]).capitalize()


def format_day_range(days):
    nums = [get_day_number(day) for day in days]
    nums = [num for num in nums if num > 0]
    if not nums:
        return "TBA"
    return str(min(nums)) if min(nums) == max(nums) else f"{min(nums)} - {max(nums)}"


def create_journey_arc(grouped_days):
    chapters = []
    current_city = None
    current_days = []
    current_rows = []
    for day, rows in grouped_days.items():
        city = get_primary_city(rows) or "Journey"
        if current_city is None:
            current_city = city
            current_days = [day]
            current_rows = list(rows)
        elif city == current_city:
            current_days.append(day)
            current_rows.extend(rows)
        else:
            chapters.append({"chapter": current_city, "days": format_day_range(current_days), "experience": describe_city_experience(current_rows)})
            current_city = city
            current_days = [day]
            current_rows = list(rows)
    if current_city is not None:
        chapters.append({"chapter": current_city, "days": format_day_range(current_days), "experience": describe_city_experience(current_rows)})
    return chapters


def create_day_title(day_rows):
    city = get_primary_city(day_rows)
    has_arrival = any(get_row_type(row) == "Arrival" for row in day_rows)
    has_departure = any(get_row_type(row) == "Departure" for row in day_rows)
    has_transfer = any(get_row_type(row) == "Transfer" for row in day_rows)
    if has_arrival and city:
        return f"Welcome to {city}"
    if has_departure and has_transfer and city:
        return f"Final transfer in {city}"
    if has_departure and city:
        return f"Final arrangements in {city}"
    for item_type in DAY_PRIORITY_TYPES:
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
        return f"Welcome to {city}. After arrival, the day is designed to keep things simple and comfortable as you settle into your accommodation."
    if has_departure and city:
        return f"Today marks the end of your arranged services in {city}. Your final transfer arrangements are listed below."
    if transports and city:
        return f"Your journey continues with arranged travel connected to {city}. The day is structured to keep the route clear, comfortable, and easy to follow."
    if activities and city:
        return f"The day is centred around {activities[0].get('title', 'your included experience')} in {city}. The remaining time can be shaped around your own pace and interests."
    if transfers and city:
        return f"Today’s arrangements in {city} are designed to keep the journey smooth and easy to follow."
    if leisure and city:
        return f"Enjoy time at leisure in {city}. This is a good opportunity to explore independently, relax, or add optional experiences."
    return f"Today is part of your stay in {city}, with arrangements listed below." if city else "Today’s arrangements are listed below."


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
    has_self_transfer = any("self transfer" in row.get("details", "").lower() for row in transfer_rows)
    if has_private_transfer and has_self_transfer:
        add_unique(included, "Transfers as listed, including private and self-guided transfers")
    elif has_private_transfer:
        add_unique(included, "Private transfers as listed in the itinerary")
    elif has_self_transfer:
        add_unique(included, "Self-guided transfers as listed in the itinerary")
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


def create_activity_inclusions(parsed_rows):
    """
    Returns activity-level inclusion details for a dedicated inclusions section.

    The day-by-day itinerary stays light, while this section preserves the
    supplier inclusions for every activity that has them.
    """

    activity_inclusions = []

    for row in parsed_rows:
        if get_row_type(row) != "Activity":
            continue

        title = row.get("title", "").strip()
        includes = row.get("includes", []) or []

        if isinstance(includes, str):
            includes = [item.strip() for item in includes.split(",") if item.strip()]
        else:
            includes = [str(item).strip() for item in includes if item and str(item).strip()]

        if not title or not includes:
            continue

        activity_inclusions.append({
            "day": row.get("day", "").strip(),
            "city": row.get("city", "").strip(),
            "title": title,
            "time": row.get("time", "").strip(),
            "meeting_point": row.get("meeting_point", "").strip(),
            "includes": includes,
        })

    return activity_inclusions


def create_whats_not_included(parsed_rows):
    return [
        "International flights unless specifically listed",
        "Meals unless specifically stated",
        "Drinks unless specifically stated",
        "Porterage unless specified",
        "Travel insurance",
        "Optional upgrades and personal expenses",
        "City taxes or local fees, where applicable",
    ]


def create_final_note(parsed_rows, grouped_days):
    trip_title = create_trip_title(parsed_rows, grouped_days)
    cities = get_unique_cities(parsed_rows)
    destinations = ", ".join(cities)
    text = " ".join(row.get("details", "").lower() for row in parsed_rows)
    themes = []
    if "train" in text or "rail" in text:
        themes.append("scenic rail journeys")
    if "cruise" in text:
        themes.append("coastal crossings")
    if "fjord" in text:
        themes.append("fjord landscapes")
    if "northern light" in text or "aurora" in text:
        themes.append("Northern Lights experiences")
    if "walking tour" in text or "guide" in text or "guided" in text:
        themes.append("guided local experiences")
    if "food" in text or "dinner" in text or "tasting" in text:
        themes.append("local food culture")
    if not themes:
        themes = ["comfortable travel arrangements", "time to explore at your own pace"]
    theme_text = ", ".join(themes)
    if destinations:
        return f"The {trip_title} is designed to make the journey through {destinations} feel clear, comfortable, and memorable. You will experience {theme_text} with enough structure to feel taken care of, and enough flexibility to make the journey your own."
    return f"The {trip_title} is designed to make the journey feel clear, comfortable, and memorable, with enough structure to feel taken care of and enough flexibility to make the journey your own."

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
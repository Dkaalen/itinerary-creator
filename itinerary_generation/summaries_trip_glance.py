"""Build the trip-glance summary table."""

from __future__ import annotations

from itinerary_generation.common import (
    destination_cities_for_row,
    get_day_count,
    get_row_type,
    get_unique_cities,
    has_self_drive_markers,
    is_valid_destination_city,
    main_rows_only,
)
from itinerary_generation.cover_route import route_cities_with_return
from itinerary_generation.group_tour_rendering import group_tour_package_from_rows
from itinerary_generation.group_tours import is_group_tour_overview


def create_trip_glance(parsed_rows, grouped_days):
    parsed_rows = main_rows_only(parsed_rows)
    cities = route_cities_with_return(parsed_rows) or get_unique_cities(parsed_rows)
    day_count = get_day_count(grouped_days)
    nights = max(day_count - 1, 0)

    # The Destinations field is owned by confirmed overnight stays.  Start and
    # End are trip endpoints, so a clean final departure city can still be shown
    # even when it is not another overnight stay.
    endpoint_cities = [
        city
        for row in parsed_rows
        for city in destination_cities_for_row(row)
        if is_valid_destination_city(city)
    ]
    start_city = endpoint_cities[0] if endpoint_cities else (cities[0] if cities else "TBA")
    end_city = endpoint_cities[-1] if endpoint_cities else (cities[-1] if cities else "TBA")
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

    group_tour_package = group_tour_package_from_rows(parsed_rows)
    group_tour_rows = [row for row in parsed_rows if is_group_tour_overview(row)]

    travel_style_parts = []

    if group_tour_package is not None or group_tour_rows:
        # Group-tour overviews are packaged guided products, not independent journeys.
        # Use every title source accepted by ``is_group_tour_overview`` so the
        # classification cannot disagree with the detector.
        group_tour_text = " ".join(
            str(row.get(field, ""))
            for row in group_tour_rows
            for field in ("title", "original_title", "details")
        ).lower() + " " + (group_tour_package.title.lower() if group_tour_package is not None else "")
        if "small" in group_tour_text:
            travel_style = "Guided small-group tour"
        else:
            travel_style = "Guided group tour"
    elif has_self_drive_markers(parsed_rows):
        if hotel_rows:
            travel_style_parts.append("planned stays")
        travel_style_parts.append("scenic self-drive routes")
        if activity_rows:
            travel_style_parts.append("selected experiences")
        travel_style = "Self-drive journey with " + ", ".join(travel_style_parts)
    else:
        if has_private_transfer:
            travel_style_parts.append("private transfers")

        if any(get_row_type(row) in {"Train", "Flight", "Cruise", "Ferry", "Transport"} for row in parsed_rows):
            travel_style_parts.append("scenic transport")

        if activity_rows:
            travel_style_parts.append("guided experiences")

        if hotel_rows:
            travel_style_parts.append("arranged accommodation")

        if travel_style_parts:
            travel_style = "Independent journey with " + ", ".join(travel_style_parts)
        else:
            travel_style = "Independent journey with arranged services"

    hotel_level = "Hotels as specified in the itinerary"

    if hotel_rows:
        hotel_level = "Accommodation as listed"

        if has_breakfast:
            hotel_level += ", breakfast included where specified"

    night_word = "night" if nights == 1 else "nights"

    return {
        "Duration": f"{day_count} days / {nights} {night_word}",
        "Start": start_city,
        "End": end_city,
        "Destinations": destinations,
        "Travel Style": travel_style,
        "Hotel Level": hotel_level,
    }

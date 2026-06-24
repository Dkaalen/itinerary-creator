from __future__ import annotations

import re

from itinerary_generation.activity_titles import (
    create_client_activity_title,
    is_bad_raw_day_title,
    normalize_client_day_title,
)
from itinerary_generation.common import clean_client_title, get_primary_city, get_row_type, has_hotel
from itinerary_generation.nutshell_domain import resolve_nutshell_journey
from itinerary_generation.group_tour_rendering import group_tour_day_title
from itinerary_generation.transport import (
    get_primary_transport_title,
    has_airport_arrival_transfer,
    has_only_departure_arrangements,
)
from place_aliases import country_for_place
from text_polish import polish_title

def create_day_title(day_rows, *, visit_context=None):
    city = get_primary_city(day_rows)

    def arrival_title() -> str:
        if getattr(visit_context, "is_return_visit", False) and city:
            return f"Return to {city}"
        return f"Welcome to {country_for_place(city) or city}" if country_for_place(city) == "Iceland" else f"Welcome to {city}"

    has_arrival = any(get_row_type(row) == "Arrival" for row in day_rows)
    has_departure = any(get_row_type(row) == "Departure" for row in day_rows)
    hotel_present = has_hotel(day_rows)
    transport_title = get_primary_transport_title(day_rows)
    activity_rows = [row for row in day_rows if get_row_type(row) == "Activity"]
    overview_rows = [row for row in day_rows if get_row_type(row) == "Day Overview"]

    if has_only_departure_arrangements(day_rows) and city:
        return f"Departure from {city}"

    if has_arrival and city:
        return arrival_title()

    # Colleague format often starts with a transfer + hotel, without an explicit
    # Arrival row. Treat airport/city-centre transfer + accommodation as arrival
    # before allowing the transfer text to become the title.
    if hotel_present and not activity_rows and has_airport_arrival_transfer(day_rows) and city:
        return arrival_title()

    group_tour_title = group_tour_day_title(day_rows)
    if group_tour_title:
        return group_tour_title

    # Real day/activity headings should beat supplier overview snippets such as
    # "Day 1: Arrival Reykjavík, pick-up minibus". Those snippets are useful
    # logistics, but they are not clear client-facing day titles.
    if activity_rows:
        title = create_client_activity_title(activity_rows[0])
        if title and not is_bad_raw_day_title(title):
            return normalize_client_day_title(title, activity_rows[0])

    # Day overview rows may drive the title only when no better activity title
    # exists, and never when they look like admin/logistics copy.
    for overview in overview_rows:
        overview_text = f'{overview.get("title", "")} {overview.get("details", "")}'.strip()
        lower_overview = overview_text.lower()
        if re.search(r"rental\s+(?:vehicle|car|suv)|pick\s*up\s+rental|pickup\s+rental|drop\s+vehicle|return\s+vehicle", lower_overview):
            continue
        match = re.search(r"\bDay\s*\d+\s*:\s*([^\n|]+)", overview_text, flags=re.IGNORECASE)
        if match:
            candidate = clean_client_title(match.group(1).strip())
            if not is_bad_raw_day_title(candidate):
                return candidate

    # Route-aware scenic journeys should keep their destination in the day title,
    # even when the row has been reclassified from Activity to Transport.
    for row in day_rows:
        nutshell_journey = resolve_nutshell_journey(row)
        if nutshell_journey is not None:
            route_title = normalize_client_day_title(nutshell_journey.client_title, row)
            if route_title:
                return route_title

    # Travel days with a hotel check-in should be titled by the main travel
    # movement rather than by a later evening activity or transfer.
    if hotel_present and transport_title:
        return transport_title

    if has_departure and city:
        return f"Departure from {city}"

    if transport_title:
        return transport_title

    priority_order = [
        # On hotel-only relocation/check-in days, the accommodation is the
        # client-facing point of the day. A raw private-transfer sentence such
        # as "Enjoy a private transfer from your accommodation to your new
        # accommodation" should stay in Travel Arrangements, not become the
        # day heading.
        "Hotel",
        "Transfer",
        "Leisure",
    ]

    for item_type in priority_order:
        for row in day_rows:
            if get_row_type(row) == item_type:
                title = row.get("title", "").strip()
                if item_type == "Hotel":
                    hotel_text = f'{row.get("hotel_name", "")} {row.get("room_category", "")} {row.get("details", "")}'
                    if re.search(r"glass\s+igloo|santa'?s\s+igloos|igloo\s+with\s+alcove", hotel_text, flags=re.IGNORECASE):
                        return "Glass Igloo Stay in Rovaniemi"
                    if city:
                        return arrival_title()

                if title:
                    if item_type == "Leisure" and city:
                        return f"A day at leisure in {city}"
                    clean_title = normalize_client_day_title(title, row)
                    return clean_title or title

    return "Day at leisure"


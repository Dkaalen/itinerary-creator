"""Day-intro orchestration for client-facing itinerary copy."""

from __future__ import annotations

import re

from itinerary_generation.client_text_decisions import client_activity_intro, client_group_tour_intro
from itinerary_generation.common import (
    TRANSPORT_TYPES,
    get_activity_text,
    get_primary_city,
    get_row_type,
    has_hotel,
    normalize_detail_level,
)
from itinerary_generation.content_engine import is_supplier_day_row
from itinerary_generation.day_activity_text import get_client_activity_phrase
from itinerary_generation.day_arrival_text import _arrival_display_destination, _arrival_transfer_phrase
from itinerary_generation.day_group_tour_text import (
    _extract_group_tour_overview_start_time,
    _is_group_tour_start_day,
    _natural_group_tour_focus,
)
from itinerary_generation.day_intro_activity import _activity_day_intro
from itinerary_generation.day_intro_arrival import (
    _explicit_transfer_airport,
    _has_destination_hotel,
    _welcome_arrival_intro,
)
from itinerary_generation.day_intro_route import _premium_route_intro, _route_summary_from_rows
from itinerary_generation.day_route_text import _canonical_route_city, create_travel_route_label
from itinerary_generation.destination_copy import (
    destination_arrival_intro,
    destination_stay_intro,
    leisure_description,
)
from itinerary_generation.route_intelligence import route_intro_for_day
from itinerary_generation.transport import (
    get_first_transfer_title,
    get_route_points_for_transport,
    get_transfer_travel_title,
    has_airport_arrival_transfer,
    has_only_departure_arrangements,
    is_route_transfer,
)
from itinerary_generation.transport_safety import base_destination_from_terminal
from parser_modules.common import extract_route_points


def _group_tour_start_intro(day_rows, activities, city_text):
    activity_title = get_client_activity_phrase(activities[0]) if activities else "the first included experience"
    start_time = _extract_group_tour_overview_start_time(day_rows)
    if start_time:
        pickup_window = start_time[:1].lower() + start_time[1:]
        pickup_sentence = f"Pick-up is scheduled {pickup_window} before you travel with your guide into {city_text}."
    else:
        pickup_sentence = f"After morning pick-up, travel with your guide into {city_text}."
    focus = _natural_group_tour_focus(activity_title)
    return (
        f"Your guided group tour begins today. {pickup_sentence} "
        f"This first stage is structured around {focus}, with the route, stops and overnight arrangements handled as part of the guided programme."
    )


def _departure_only_intro(day_rows, city, detail_level):
    transfer_title = get_first_transfer_title(day_rows).lower()
    has_transfer_row = any(get_row_type(row) == "Transfer" for row in day_rows)
    if not has_transfer_row:
        if detail_level == "Rich descriptive":
            return f"Your journey comes to a close in {city} today, with time for check-out before you continue your travels home."
        return f"Your journey comes to a close in {city} today before your journey home."
    if any(marker in transfer_title for marker in ("self-guided", "self transfer", "self-arranged", "self arranged")):
        airport = _explicit_transfer_airport(day_rows) or f"{city} Airport"
        return f"After check-out, please make your own way to {airport} for your onward journey."
    airport = _explicit_transfer_airport(day_rows) or f"{city} Airport"
    if detail_level == "Rich descriptive":
        return f"Your journey comes to a close today. After check-out, your arranged transfer will take you from your hotel to {airport} for your onward journey."
    return f"After check-out, your arranged transfer will take you from your hotel to {airport} for your onward journey."


def _arrival_intro(day_rows, city, city_text, activities, detail_level, visit_context):
    destination = _arrival_display_destination(city)
    transfer_phrase = _arrival_transfer_phrase(day_rows)
    if activities:
        activity_title = get_client_activity_phrase(activities[0])
        activity_text = get_activity_text(activities[0])
        activity_city = str(activities[0].get("city", "") or "").strip()
        city_for_activity = activity_city or city_text
        activity_intro = _activity_day_intro(activity_title, city_for_activity, activity_text, detail_level)
        prefix = "Return to" if getattr(visit_context, "is_return_visit", False) else "Welcome to"
        return f"{prefix} {destination}. {transfer_phrase} {activity_intro}"
    return destination_arrival_intro(
        city,
        transfer_phrase,
        detail_level,
        display_destination=destination,
        rows=day_rows,
        visit_context=visit_context,
    )


def _airport_hotel_arrival_intro(day_rows, city, detail_level, visit_context):
    destination = _arrival_display_destination(city)
    transfer_phrase = _arrival_transfer_phrase(day_rows)
    return destination_arrival_intro(
        city,
        transfer_phrase,
        detail_level,
        display_destination=destination,
        rows=day_rows,
        visit_context=visit_context,
    )


def _departure_intro(day_rows, city, detail_level):
    departure_text = " ".join(
        f'{row.get("title", "")} {row.get("details", "")} {row.get("original_title", "")}'
        for row in day_rows
    ).lower()
    if any(marker in departure_text for marker in ("self transfer", "self-arranged", "self arranged", "own way")):
        airport = _explicit_transfer_airport(day_rows) or f"{city} Airport"
        return f"After check-out, please make your own way to {airport} for your onward journey."
    if detail_level == "Elegant concise":
        return f"After check-out, your final arrangements in {city} are kept simple."
    if detail_level == "Rich descriptive":
        return f"After check-out, your final arrangements in {city} are kept smooth and straightforward, giving the journey an easy and well-organised finish."
    return f"After check-out, your final arrangements in {city} are kept simple and easy to follow."


def _tallinn_activity_intro(day_rows, detail_level):
    has_overnight_train = any(
        get_row_type(row) == "Train" and "overnight" in f'{row.get("title", "")} {row.get("details", "")}'.lower()
        for row in day_rows
    )
    if has_overnight_train:
        if detail_level == "Elegant concise":
            return "Enjoy a day trip from Helsinki to Tallinn before returning for your overnight train north."
        if detail_level == "Rich descriptive":
            return "Cross from Helsinki to Tallinn for a memorable day trip, with time to experience the atmosphere of the historic Old Town before returning to Helsinki for your overnight train north."
        return "Enjoy a day trip from Helsinki to Tallinn, with time to explore the Old Town before returning to Helsinki for your overnight train north."
    if detail_level == "Elegant concise":
        return "Enjoy a day trip from Helsinki to Tallinn before continuing with the next stage of the trip."
    if detail_level == "Rich descriptive":
        return "Cross from Helsinki to Tallinn for a memorable day trip, with time to experience the historic Old Town before returning to Helsinki for the next stage of the trip."
    return "Enjoy a day trip from Helsinki to Tallinn, with time to explore the Old Town before the next stage of the trip."


def _activity_led_intro(day_rows, activities, transports, route_transfers, city, city_text, detail_level, visit_context):
    activity_title = get_client_activity_phrase(activities[0])
    activity_text = get_activity_text(activities[0])

    if is_supplier_day_row(activities[0]):
        source_text = get_activity_text(activities[0])
        return client_group_tour_intro(activity_title, city_text, source_text)

    combined_activity_text = " ".join(get_activity_text(row) for row in activities)
    if "tallinn" in combined_activity_text.lower():
        return _tallinn_activity_intro(day_rows, detail_level)

    activity_city = str(activities[0].get("city", "") or "").strip()
    city_for_activity = city_text
    if activity_city and city_text and activity_city.lower() != city_text.lower():
        city_for_activity = ""

    if transports or route_transfers:
        intro = _activity_day_intro(activity_title, city_for_activity or city_text, activity_text, detail_level)
        if has_hotel(day_rows) and city:
            return f"{_welcome_arrival_intro(city, detail_level, with_activity=True, visit_context=visit_context)} {intro}"
        return intro

    if not has_hotel(day_rows) or (not transports and not route_transfers):
        if detail_level == "Elegant concise":
            return f"{activity_title} is the main arranged experience in {city_text}, with the rest of the day kept flexible."
        return client_activity_intro(activity_title, city_for_activity or city_text, activity_text)

    return ""


def _destination_city_from_travel_rows(day_rows):
    invalid_destination_words = {
        "hotel",
        "station",
        "airport",
        "accommodation",
        "your accommodation",
        "self transfer",
        "private airport to hotel",
        "private hotel to airport",
    }
    travel_rows = [
        row
        for row in day_rows
        if get_row_type(row) in TRANSPORT_TYPES or get_row_type(row) == "Transfer" or is_route_transfer(row)
    ]
    destination_city = ""
    for row in travel_rows:
        origin, route_destination = get_route_points_for_transport(row) if get_row_type(row) in TRANSPORT_TYPES else ("", "")
        if not route_destination and is_route_transfer(row):
            _, route_destination = extract_route_points(get_transfer_travel_title(row))
        candidate = str(route_destination or "").strip()
        lower_candidate = candidate.lower()
        if candidate and lower_candidate not in invalid_destination_words and not any(
            bad in lower_candidate for bad in ["shower", "sink", "wc", "benefits", "made bed"]
        ):
            destination_city = _canonical_route_city(base_destination_from_terminal(candidate) or candidate)
            continue
        title_match = re.search(
            r"\bto\s+([A-Za-zÀ-ÿøØåÅäÄöÖ]+(?:\s+[A-Za-zÀ-ÿøØåÅäÄöÖ]+)?)\s*$",
            str(row.get("title", "")),
            flags=re.IGNORECASE,
        )
        if title_match and title_match.group(1).lower() not in invalid_destination_words:
            destination_city = _canonical_route_city(base_destination_from_terminal(title_match.group(1)) or title_match.group(1))
    return destination_city


def _transport_led_intro(day_rows, transports, route_transfers, city, detail_level, visit_context):
    transport_context = " ".join(
        f'{row.get("title", "")} {row.get("details", "")} {row.get("original_title", "")}'
        for row in transports + route_transfers
    ).lower()
    if any(marker in transport_context for marker in ("norway in a nutshell", "nærøyfjord", "naeroyfjord", "flåm train", "flam train")):
        premium_route_intro = route_intro_for_day(day_rows, detail_level)
        if premium_route_intro:
            return premium_route_intro
        return f"Follow the Norway in a Nutshell route towards {city}, with the rail, fjord and road segments presented together as one signature scenic journey."

    has_flight_transport = any(get_row_type(row) == "Flight" for row in transports)
    if has_flight_transport and has_hotel(day_rows) and city and _has_destination_hotel(day_rows, city):
        return _welcome_arrival_intro(city, detail_level, visit_context=visit_context)

    route_label = create_travel_route_label(day_rows)
    if route_label:
        if detail_level == "Elegant concise":
            return f"Travel from {route_label}."
        if detail_level == "Rich descriptive":
            return f"Travel from {route_label} today, with the main transfer details laid out clearly in the itinerary."
        return f"Travel from {route_label}, with the day focused on the planned route."

    has_primary_transport_row = any(get_row_type(row) in TRANSPORT_TYPES for row in transports + route_transfers)
    if has_primary_transport_row:
        premium_route_intro = route_intro_for_day(day_rows, detail_level)
        if premium_route_intro:
            return premium_route_intro

    route_origin, route_destination, route_mode = _route_summary_from_rows(day_rows)
    premium_intro = _premium_route_intro(route_origin, route_destination, route_mode, detail_level)
    if premium_intro:
        return premium_intro

    display_city = _destination_city_from_travel_rows(day_rows) or city
    if detail_level == "Elegant concise":
        return f"Travel to {display_city} with the listed arrangements."
    if detail_level == "Rich descriptive":
        return f"Travel towards {display_city} today, with the main transfer details laid out clearly in the itinerary."
    return f"Travel to {display_city} with the listed arrangements."


def _transfer_led_intro(day_rows, transfers, city, detail_level):
    transfer_text = " ".join(f'{row.get("title", "")} {row.get("details", "")}' for row in transfers).lower()
    if any(marker in transfer_text for marker in ("self transfer", "self-drive", "drive", "car rental")):
        if "jökulsárlón" in transfer_text or "jokulsarlon" in transfer_text:
            return "Set out on a scenic self-drive day towards Jökulsárlón, with the route and accommodation arranged so you can travel at your own pace."
        if "reykjav" in transfer_text:
            return "Continue your self-drive journey back towards Reykjavík, with time to enjoy the route before checking in to your next stay."
        if "car rental" in transfer_text or "rental" in transfer_text:
            return "Pick up your rental vehicle today and begin the self-drive portion of the journey, with the route planned clearly for the day ahead."
        return f"Continue your stay in {city}, with the transfer between accommodations kept clear in the arrangements below."
    if detail_level == "Elegant concise":
        return f"Today’s logistics in {city} are kept smooth and simple."
    if detail_level == "Rich descriptive":
        return f"Today’s arrangements in {city} are kept clear and comfortable, with the key logistics handled in an easy-to-follow way."
    return f"Today’s arrangements in {city} are kept smooth and easy to follow."


def _city_stay_intro(day_rows, city, detail_level, visit_context):
    if has_hotel(day_rows):
        return destination_stay_intro(city, detail_level, rows=day_rows, visit_context=visit_context)
    if detail_level == "Elegant concise":
        return f"This is part of your stay in {city}, with arrangements listed below."
    if detail_level == "Rich descriptive":
        return f"This is part of your stay in {city}, with the day’s arrangements laid out clearly so the experience feels relaxed and easy to follow."
    return f"This is part of your stay in {city}, with arrangements included as listed below."


def create_day_intro(day_rows, detail_level="Standard client itinerary", *, visit_context=None):
    """Create a clear, client-facing day intro."""

    detail_level = normalize_detail_level(detail_level)
    city = get_primary_city(day_rows)
    city_text = city or "the experience area"

    has_arrival = any(get_row_type(row) == "Arrival" for row in day_rows)
    has_departure = any(get_row_type(row) == "Departure" for row in day_rows)

    activities = [row for row in day_rows if get_row_type(row) == "Activity"]
    transports = [row for row in day_rows if get_row_type(row) in TRANSPORT_TYPES]
    transfers = [row for row in day_rows if get_row_type(row) == "Transfer"]
    route_transfers = [row for row in transfers if is_route_transfer(row)]
    leisure = [row for row in day_rows if get_row_type(row) == "Leisure"]

    if _is_group_tour_start_day(day_rows):
        return _group_tour_start_intro(day_rows, activities, city_text)
    if has_only_departure_arrangements(day_rows) and city:
        return _departure_only_intro(day_rows, city, detail_level)
    if has_arrival and city:
        return _arrival_intro(day_rows, city, city_text, activities, detail_level, visit_context)
    if not transports and has_hotel(day_rows) and has_airport_arrival_transfer(day_rows) and city:
        return _airport_hotel_arrival_intro(day_rows, city, detail_level, visit_context)
    if has_departure and city:
        return _departure_intro(day_rows, city, detail_level)
    if activities:
        activity_intro = _activity_led_intro(
            day_rows,
            activities,
            transports,
            route_transfers,
            city,
            city_text,
            detail_level,
            visit_context,
        )
        if activity_intro:
            return activity_intro
    if (transports or route_transfers) and city:
        return _transport_led_intro(day_rows, transports, route_transfers, city, detail_level, visit_context)
    if transfers and city:
        return _transfer_led_intro(day_rows, transfers, city, detail_level)
    if leisure and city:
        return leisure_description(city, day_rows)
    if city:
        return _city_stay_intro(day_rows, city, detail_level, visit_context)
    return "The day’s arrangements are listed below."

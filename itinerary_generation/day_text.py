"""Create client-facing day intro text."""

from __future__ import annotations

import re

from itinerary_generation.common import (
    TRANSPORT_TYPES,
    get_activity_text,
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
from itinerary_generation.content_engine import is_supplier_day_row
from itinerary_generation.day_activity_text import get_client_activity_phrase, _activity_phrase_with_city
from itinerary_generation.day_arrival_text import _arrival_display_destination, _arrival_transfer_phrase
from itinerary_generation.day_group_tour_text import (
    _extract_group_tour_overview_start_time,
    _is_group_tour_start_day,
    _natural_group_tour_focus,
)
from itinerary_generation.day_route_text import _canonical_route_city, create_travel_route_label
from parser_modules.common import extract_route_points


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
            pickup_window = start_time[:1].lower() + start_time[1:]
            pickup_sentence = f"Pick-up is scheduled {pickup_window} before you travel with your guide into {city_text}."
        else:
            pickup_sentence = f"After morning pick-up, travel with your guide into {city_text}."
        focus = _natural_group_tour_focus(activity_title)
        return (
            f"Your guided group tour begins today. {pickup_sentence} "
            f"This first stage is structured around {focus}, with the route, stops and overnight arrangements handled as part of the guided programme."
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

        if is_supplier_day_row(activities[0]):
            source_text = get_activity_text(activities[0])
            focus = _natural_group_tour_focus(activity_title, source_text)
            if "whale" in source_text.lower() and "hauganes" in source_text.lower():
                return (
                    "Your guided group tour continues today to Hauganes for Whale Watching before returning to Reykjavík. "
                    "The day is organised around the included boat experience and the final guided route back to the capital."
                )
            return (
                f"Your guided group tour continues today with {focus}. "
                "The day is organised around the included route, guided stops and overnight arrangements, "
                "so you can focus on the landscapes and places visited along the way."
            )

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
            return (
                f"Today is centred on {activity_with_city}, with the surrounding schedule kept clear and comfortable. "
                "This gives the experience space in the day without making the itinerary feel rushed."
            )

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
        transfer_text = " ".join(f'{row.get("title", "")} {row.get("details", "")}' for row in transfers).lower()
        if "self transfer" in transfer_text or "self-drive" in transfer_text or "drive" in transfer_text or "car rental" in transfer_text:
            if "jökulsárlón" in transfer_text or "jokulsarlon" in transfer_text:
                return "Set out on a scenic self-drive day towards Jökulsárlón, with the route and accommodation arranged so you can travel at your own pace."
            if "reykjav" in transfer_text:
                return "Continue your self-drive journey back towards Reykjavík, with time to enjoy the route before checking in to your next stay."
            if "car rental" in transfer_text or "rental" in transfer_text:
                return "Pick up your rental vehicle today and begin the self-drive portion of the journey, with the route planned clearly for the day ahead."
            return f"Continue by self-drive or self transfer in {city}, with the day structured to keep the route clear and easy to follow."
        if detail_level == "Elegant concise":
            return f"Today’s logistics in {city} are kept smooth and simple."
        if detail_level == "Rich descriptive":
            return f"Today’s arrangements in {city} are kept clear and comfortable, with the key logistics handled in an easy-to-follow way."
        return f"Today’s arrangements in {city} are kept smooth and easy to follow."

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

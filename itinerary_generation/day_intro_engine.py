"""Single source of truth for client-facing day intro text."""

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
from itinerary_generation.day_activity_text import get_client_activity_phrase
from itinerary_generation.client_text_decisions import client_activity_intro, client_group_tour_intro
from itinerary_generation.day_arrival_text import _arrival_display_destination, _arrival_transfer_phrase
from itinerary_generation.day_group_tour_text import (
    _extract_group_tour_overview_start_time,
    _is_group_tour_start_day,
    _natural_group_tour_focus,
)
from itinerary_generation.day_route_text import _canonical_route_city, create_travel_route_label
from itinerary_generation.destination_copy import leisure_description, travel_day_intro
from parser_modules.common import extract_route_points
from text_polish import polish_title
from itinerary_generation.transport_model import get_transport_source_text
from itinerary_generation.transport_safety import base_destination_from_terminal, normalize_transport_place
from itinerary_generation.route_intelligence import route_intro_for_day, route_profile_for_places



def _explicit_transfer_airport(day_rows) -> str:
    """Return an explicit airport mentioned in transfer rows, preserving input.

    This prevents generic destination logic from inventing airports such as
    "Levi Airport" when the actual row says Kittilä Airport.
    """

    for row in day_rows:
        if get_row_type(row) != "Transfer":
            continue
        text = get_transport_source_text(row)
        match = re.search(r"\b(?:to|from)\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?\s+Airport)\b", text, flags=re.IGNORECASE)
        if not match:
            all_airports = re.findall(r"\b([A-ZÅÄÖÆØ][A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{1,40}?\s+Airport)\b", text)
            if all_airports:
                airport = normalize_transport_place(all_airports[-1])
                if airport:
                    return airport
            continue
        airport = normalize_transport_place(match.group(1))
        if airport and airport.lower() not in {"airport", "the airport"}:
            return airport
    return ""


def _activity_day_intro(activity_title: str, city: str, source_text: str, detail_level: str = "") -> str:
    """Compatibility wrapper around the shared activity-intro decision engine."""

    return client_activity_intro(activity_title, city, source_text)


def _group_tour_intro(activity_title: str, city: str, source_text: str) -> str:
    """Compatibility wrapper around the shared group-tour decision engine."""

    return client_group_tour_intro(activity_title, city, source_text)


def _activity_intro(title: str, city: str) -> str:
    """Compatibility wrapper around the shared activity-intro decision engine."""

    return client_activity_intro(title, city)


def _group_tour_intro_from_source(title: str, source: str) -> str:
    """Compatibility wrapper around the shared group-tour decision engine."""

    return client_group_tour_intro(title, "the route", source)


def _welcome_arrival_intro(city: str, detail_level: str, *, with_activity: bool = False) -> str:
    destination = _arrival_display_destination(city)
    if with_activity:
        return f"Welcome to {destination}."
    if detail_level == "Elegant concise":
        return f"Welcome to {destination}. Time is kept relaxed after arrival so you can settle in."
    if detail_level == "Rich descriptive":
        return f"Welcome to {destination}. After arrival, the day is kept relaxed so you can check in, settle into your accommodation and get your first impression of the destination."
    return f"Welcome to {destination}. After arrival, enjoy time to settle in."


def _has_destination_hotel(day_rows: list[dict], city: str) -> bool:
    city_key = str(city or "").strip().lower()
    if not city_key:
        return False
    return any(get_row_type(row) == "Hotel" and str(row.get("city", "")).strip().lower() == city_key for row in day_rows)



def _route_summary_from_rows(day_rows: list[dict]) -> tuple[str, str, str]:
    """Return origin, destination and main mode for route-led day intros."""

    origin = ""
    destination = ""
    mode = ""
    for row in day_rows:
        row_type = get_row_type(row)
        if row_type not in TRANSPORT_TYPES:
            continue
        if not mode:
            row_text = f'{row.get("title", "")} {row.get("details", "")} {row.get("original_title", "")}'.lower()
            if row_type == "Train" or "train" in row_text:
                mode = "train"
            elif row_type == "Flight" or "flight" in row_text:
                mode = "flight"
            elif row_type == "Cruise" or "cruise" in row_text:
                mode = "cruise"
            elif row_type == "Ferry" or "ferry" in row_text:
                mode = "ferry"
            elif "coach" in row_text or "bus" in row_text:
                mode = "coach"
            else:
                mode = row_type.lower()
        route_origin, route_destination = get_route_points_for_transport(row)
        if route_origin and not origin:
            origin = _canonical_route_city(base_destination_from_terminal(route_origin) or route_origin)
        if route_destination:
            destination = _canonical_route_city(base_destination_from_terminal(route_destination) or route_destination)
    return origin, destination, mode


def _premium_route_intro(origin: str, destination: str, mode: str, detail_level: str = "") -> str:
    origin = _canonical_route_city(origin)
    destination = _canonical_route_city(destination)
    mode = str(mode or "").lower()
    if not destination:
        return ""
    if origin and origin.lower() == destination.lower():
        origin = ""
    if mode == "nutshell" and not origin:
        return ""

    profile_mode = "norway_in_a_nutshell" if mode == "nutshell" else "coastal_cruise" if mode == "coastal_cruise" else mode
    profile = route_profile_for_places(origin, destination, profile_mode)
    if profile:
        return profile.intro

    if destination.lower() == "kristiansand":
        if origin:
            return f"Travel south from {origin} to Kristiansand, with the coach journey connecting the route to Norway’s southern coast." if mode == "coach" else f"Travel south from {origin} to Kristiansand, with the day shaped around the move into Norway’s southern coast."
        return "Travel towards Kristiansand today, with the day shaped around Norway’s southern coastal charm."
    if destination.lower() == "stavanger":
        if origin:
            return f"Travel from {origin} to Stavanger by train, continuing from the southern coast towards Norway’s fjord country." if mode == "train" else f"Travel from {origin} to Stavanger, continuing towards Norway’s fjord country."
        return "Travel towards Stavanger today, continuing towards Norway’s fjord country."
    if destination.lower() == "bergen" and mode in {"cruise", "ferry"}:
        if origin:
            return f"Travel from {origin} to Bergen by coastal cruise, with the day arranged as a coordinated port-to-hotel journey."
        return "Travel to Bergen by coastal cruise, with the day arranged as a coordinated port-to-hotel journey."
    generic_intro = travel_day_intro(origin, destination, mode)
    if generic_intro:
        return generic_intro
    if origin:
        connector = f" by {mode}" if mode in {"train", "coach", "ferry", "cruise", "flight"} else ""
        return f"Travel from {origin} to {destination}{connector}, with the day’s route and arrival arrangements grouped clearly below."
    return f"Travel to {destination}, with the day’s route and arrival arrangements grouped clearly below."

def _title_route_points(title: str, city: str = "") -> tuple[str, str]:
    """Infer coarse route endpoints from a planned day title."""

    text = str(title or "").strip()
    if not text:
        return "", polish_title(city) if city else ""
    if re.search(r"^travel\s+to\s+", text, flags=re.IGNORECASE):
        destination = re.sub(r"^travel\s+to\s+", "", text, flags=re.IGNORECASE).strip(" -:|")
        return "", polish_title(destination)
    nutshell_to = re.search(r"^norway\s+in\s+a\s+nutshell\s+to\s+(.+)$", text, flags=re.IGNORECASE)
    if nutshell_to:
        return "", polish_title(nutshell_to.group(1).strip(" -:|"))

    match = re.search(r"\bfrom\s+(.+?)\s+to\s+(.+)$", text, flags=re.IGNORECASE)
    if not match:
        match = re.search(r"^(.+?)\s+(?:→|->|to)\s+(.+)$", text, flags=re.IGNORECASE)
    if match:
        origin = polish_title(match.group(1).strip(" -:|"))
        destination = polish_title(match.group(2).strip(" -:|"))
        if origin.lower() in {"travel", "journey"}:
            origin = ""
        return origin, destination

    match = re.search(r"\bto\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+)$", text, flags=re.IGNORECASE)
    if match:
        destination = polish_title(match.group(1).strip(" -:|"))
        return "", destination
    return "", polish_title(city) if city else ""


def _travel_mode_from_title(title: str) -> str:
    lower = str(title or "").lower()
    if "norway in a nutshell" in lower:
        return "nutshell"
    if "coastal cruise" in lower or "cruise transfer" in lower:
        return "coastal_cruise"
    if "cruise" in lower:
        return "cruise"
    if "ferry" in lower:
        return "ferry"
    if "train" in lower or "rail" in lower:
        return "train"
    if "coach" in lower or "bus" in lower:
        return "coach"
    if "flight" in lower:
        return "flight"
    return ""


def _intro_for_title(title: str, city: str, pattern: str) -> str:
    if pattern == "leisure_day":
        return leisure_description(city, []) if city else "Use the day at your own pace, with time to relax, explore independently or settle into the destination."
    if pattern == "multi_activity_day":
        title_text = str(title or "").lower()
        if "tallinn" in title_text:
            return "Cross from Helsinki to Tallinn for a focused day trip, with the ferry crossings kept as logistics and the main experience centred on Tallinn’s historic Old Town."
        if "bergen" in (city or "").lower() and ("fløibanen" in title_text or "floibanen" in title_text or "walking" in title_text):
            return "Bergen is explored on foot and from above today, pairing local stories around the historic harbour with the flexible mountain viewpoint of Fløyen."
        return f"Today combines complementary experiences in {city}, with the schedule arranged so the day feels varied but easy to follow." if city else "Today combines complementary experiences, with the schedule arranged so the day feels varied but easy to follow."
    if pattern == "travel_day":
        mode = _travel_mode_from_title(title)
        origin, destination = _title_route_points(title, city)
        destination = destination or polish_title(city)
        premium_intro = _premium_route_intro(origin, destination, mode)
        if premium_intro:
            return premium_intro
        if mode == "nutshell":
            return f"Follow the Norway in a Nutshell route towards {destination}, with the rail, fjord and road segments presented together as one signature scenic journey." if destination else "Follow the Norway in a Nutshell route today, with the rail, fjord and road segments presented together as one signature scenic journey."
        if mode == "coastal_cruise":
            if origin and destination and origin.lower() != destination.lower():
                return f"Travel from {origin} to {destination} by coastal cruise, with the port transfers and sailing arranged as one coordinated door-to-door journey."
            if destination:
                return f"Travel to {destination} by coastal cruise, with the port transfers and sailing arranged as one coordinated door-to-door journey."
            return "Travel by coastal cruise today, with the port transfers and sailing arranged as one coordinated door-to-door journey."
        return f"Travel to {destination}, with the route and arrival arrangements grouped clearly below." if destination else "Today is arranged as a clear travel day, with the route and arrival details grouped below."
    if pattern == "self_drive_route_day":
        return "Today’s self-drive route is arranged to keep the journey clear and scenic, with suggested stops and overnight plans laid out in a simple way."
    if pattern == "hop_on_city_day":
        return f"Use the day flexibly to explore {city} at your own pace, with sightseeing transport arranged to make the city’s main areas easy to reach." if city else "Use the day flexibly to explore at your own pace, with sightseeing transport arranged to make the main areas easy to reach."
    if pattern == "single_activity_day":
        return client_activity_intro(title, city)
    return ""


def create_day_intro(day_rows, detail_level="Standard client itinerary"):
    """Create a clear, client-facing day intro.

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
        if (
            "self-guided" in transfer_title
            or "self transfer" in transfer_title
            or "self-arranged" in transfer_title
            or "self arranged" in transfer_title
        ):
            airport = _explicit_transfer_airport(day_rows) or f"{city} Airport"
            return f"After check-out, please make your own way to {airport} for your onward journey."
        if detail_level == "Rich descriptive":
            airport = _explicit_transfer_airport(day_rows) or f"{city} Airport"
            return f"Your journey comes to a close today. After check-out, your arranged transfer will take you from your hotel to {airport} for your onward journey."
        airport = _explicit_transfer_airport(day_rows) or f"{city} Airport"
        return f"After check-out, your arranged transfer will take you from your hotel to {airport} for your onward journey."

    if has_arrival and city:
        destination = _arrival_display_destination(city)
        transfer_phrase = _arrival_transfer_phrase(day_rows)
        if activities:
            activity_title = get_client_activity_phrase(activities[0])
            activity_text = get_activity_text(activities[0])
            activity_city = str(activities[0].get("city", "") or "").strip()
            city_for_activity = activity_city or city_text
            activity_intro = _activity_day_intro(activity_title, city_for_activity, activity_text, detail_level)
            return f"Welcome to {destination}. {transfer_phrase} {activity_intro}"
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
        departure_text = " ".join(f'{row.get("title", "")} {row.get("details", "")} {row.get("original_title", "")}' for row in day_rows).lower()
        if any(marker in departure_text for marker in ("self transfer", "self-arranged", "self arranged", "own way")):
            airport = _explicit_transfer_airport(day_rows) or f"{city} Airport"
            return f"After check-out, please make your own way to {airport} for your onward journey."
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
            return client_group_tour_intro(activity_title, city_text, source_text)

        combined_activity_text = " ".join(get_activity_text(row) for row in activities)
        if "tallinn" in combined_activity_text.lower():
            if any(get_row_type(row) == "Train" and "overnight" in f'{row.get("title", "")} {row.get("details", "")}'.lower() for row in day_rows):
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

        activity_city = str(activities[0].get("city", "") or "").strip()
        city_for_activity = city_text
        if activity_city and city_text and activity_city.lower() != city_text.lower():
            city_for_activity = ""

        if transports or route_transfers:
            intro = _activity_day_intro(activity_title, city_for_activity or city_text, activity_text, detail_level)
            if has_hotel(day_rows) and city:
                return f"{_welcome_arrival_intro(city, detail_level, with_activity=True)} {intro}"
            return intro

        if not has_hotel(day_rows) or (not transports and not route_transfers):
            if detail_level == "Elegant concise":
                return f"{activity_title} is the main arranged experience in {city_text}, with the rest of the day kept flexible."

            return client_activity_intro(activity_title, city_for_activity or city_text, activity_text)

    if (transports or route_transfers) and city:
        transport_context = " ".join(f'{row.get("title", "")} {row.get("details", "")} {row.get("original_title", "")}' for row in transports + route_transfers).lower()
        if ("norway in a nutshell" in transport_context or "nærøyfjord" in transport_context or "naeroyfjord" in transport_context or "flåm train" in transport_context or "flam train" in transport_context):
            premium_route_intro = route_intro_for_day(day_rows, detail_level)
            if premium_route_intro:
                return premium_route_intro
            return f"Follow the Norway in a Nutshell route towards {city}, with the rail, fjord and road segments presented together as one signature scenic journey."

        has_flight_transport = any(get_row_type(row) == "Flight" for row in transports)
        if has_flight_transport and has_hotel(day_rows) and city and _has_destination_hotel(day_rows, city):
            return _welcome_arrival_intro(city, detail_level)

        premium_route_intro = route_intro_for_day(day_rows, detail_level)
        if premium_route_intro:
            return premium_route_intro

        route_label = create_travel_route_label(day_rows)
        if route_label:
            route_destination = route_label.split(" to ")[-1].strip() if " to " in route_label else ""
            if detail_level == "Elegant concise":
                return f"Travel from {route_label}."
            if detail_level == "Rich descriptive":
                return f"Travel from {route_label} today, with the main transfer details laid out clearly in the itinerary."
            return f"Travel from {route_label}, with the day focused on the planned route."

        route_origin, route_destination, route_mode = _route_summary_from_rows(day_rows)
        premium_intro = _premium_route_intro(route_origin, route_destination, route_mode, detail_level)
        if premium_intro:
            return premium_intro

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
                destination_city = _canonical_route_city(base_destination_from_terminal(candidate) or candidate)
                continue
            title_match = re.search(r"\bto\s+([A-Za-zÀ-ÿøØåÅäÄöÖ]+(?:\s+[A-Za-zÀ-ÿøØåÅäÄöÖ]+)?)\s*$", str(row.get("title", "")), flags=re.IGNORECASE)
            if title_match and title_match.group(1).lower() not in invalid_destination_words:
                destination_city = _canonical_route_city(base_destination_from_terminal(title_match.group(1)) or title_match.group(1))
        display_city = destination_city or city
        has_flight_transport = any(get_row_type(row) == "Flight" for row in transports)
        if has_flight_transport and has_hotel(day_rows) and city and _has_destination_hotel(day_rows, city):
            return _welcome_arrival_intro(city, detail_level)
        if detail_level == "Elegant concise":
            return f"Travel to {display_city} with the listed arrangements."
        if detail_level == "Rich descriptive":
            return f"Travel towards {display_city} today, with the main transfer details laid out clearly in the itinerary."
        return f"Travel to {display_city} with the listed arrangements."

    if transfers and city:
        transfer_text = " ".join(f'{row.get("title", "")} {row.get("details", "")}' for row in transfers).lower()
        if "self transfer" in transfer_text or "self-drive" in transfer_text or "drive" in transfer_text or "car rental" in transfer_text:
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

    if leisure and city:
        if detail_level == "Elegant concise":
            return leisure_description(city, day_rows)
        if detail_level == "Rich descriptive":
            return leisure_description(city, day_rows)
        return leisure_description(city, day_rows)

    if city:
        if has_hotel(day_rows):
            destination = _arrival_display_destination(city)
            if detail_level == "Elegant concise":
                return f"Welcome to {destination}. Time is kept relaxed after arrival so you can settle into your accommodation."
            if detail_level == "Rich descriptive":
                return f"Welcome to {destination}. After arrival, the day is kept relaxed so you can check in, settle into your accommodation and enjoy your first impression of the destination."
            return f"Welcome to {destination}. After arrival, enjoy time to settle into your accommodation."
        if detail_level == "Elegant concise":
            return f"This is part of your stay in {city}, with arrangements listed below."
        if detail_level == "Rich descriptive":
            return f"This is part of your stay in {city}, with the day’s arrangements laid out clearly so the experience feels relaxed and easy to follow."
        return f"This is part of your stay in {city}, with arrangements included as listed below."

    return "The day’s arrangements are listed below."

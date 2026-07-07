"""Day-title intro classification helpers."""

from __future__ import annotations

from itinerary_generation.client_text_decisions import client_activity_intro
from itinerary_generation.day_intro_route import _premium_route_intro, _title_route_points, _travel_mode_from_title
from itinerary_generation.destination_copy import destination_stay_intro, leisure_description
from text_polish import polish_title


def _intro_for_title(title: str, city: str, pattern: str) -> str:
    """Return intro copy for a pre-classified day-title pattern."""

    if pattern == "leisure_day":
        return leisure_description(city, []) if city else "Today is open for independent time, with space to rest, explore locally or keep the pace flexible."
    if pattern == "stay_day":
        return destination_stay_intro(city, "Rich descriptive") if city else "Today is open for independent time, with space to rest, explore locally or keep the pace flexible."
    if pattern == "multi_activity_day":
        title_text = str(title or "").lower()
        if "tallinn" in title_text:
            return "Cross from Helsinki to Tallinn for a focused day trip, with the ferry crossings kept as logistics and the main experience centred on Tallinn’s historic Old Town."
        if "bergen" in (city or "").lower() and ("fløibanen" in title_text or "floibanen" in title_text or "walking" in title_text):
            return "Explore Bergen in two parts today, beginning with local stories around the historic harbour before using Fløibanen for flexible time above the city at Mount Fløyen."
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
        return f"Use open time flexibly to explore {city} at your own pace, with sightseeing transport arranged to make the city’s main areas easy to reach." if city else "Use open time flexibly to explore at your own pace, with sightseeing transport arranged to make the main areas easy to reach."
    if pattern == "single_activity_day":
        return client_activity_intro(title, city)
    return ""


__all__ = ["_intro_for_title"]

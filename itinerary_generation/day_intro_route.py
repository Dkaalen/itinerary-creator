"""Route-led day-intro prose helpers."""

from __future__ import annotations

from itinerary_generation.day_route_text import _canonical_route_city, create_travel_route_label
from itinerary_generation.destination_copy import travel_day_intro
from itinerary_generation.route_intelligence import route_profile_for_places


def _premium_route_intro(origin: str, destination: str, mode: str, detail_level: str = "") -> str:
    """Return premium destination-aware route copy when deterministic route facts exist."""

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
            return "Travel from {origin} to Bergen by coastal cruise, with the day arranged as a coordinated port-to-hotel journey.".format(origin=origin)
        return "Travel to Bergen by coastal cruise, with the day arranged as a coordinated port-to-hotel journey."
    generic_intro = travel_day_intro(origin, destination, mode)
    if generic_intro:
        return generic_intro
    if origin:
        connector = f" by {mode}" if mode in {"train", "coach", "ferry", "cruise", "flight"} else ""
        return f"Travel from {origin} to {destination}{connector}, with the day’s route and arrival arrangements grouped clearly below."
    return f"Travel to {destination}, with the day’s route and arrival arrangements grouped clearly below."


__all__ = ["_premium_route_intro", "create_travel_route_label"]

"""Return-visit and first-arrival repetition protection."""
from __future__ import annotations

from itinerary_generation.day_facts import DayFacts
from itinerary_generation.day_intro_context import _city


def _return_visit_intro(facts: DayFacts, profile_route_intro: str, city: str) -> str:
    """Describe a return stay from route truth instead of admin fallback copy."""

    place = city or _city(facts.end_city) or "the destination"
    destinations = [_city(item) for item in facts.route_destinations if _city(item)]
    round_trip = bool(
        place
        and len(destinations) >= 2
        and destinations[-1].casefold() == place.casefold()
        and any(item.casefold() != place.casefold() for item in destinations[:-1])
    )
    if round_trip:
        return (
            f"Head out on today’s planned journey before returning to {place}, "
            "with the travel timings and overnight stay kept together below."
        )
    if facts.has_self_drive:
        origin = _city(facts.route_origin or facts.start_city)
        if origin and origin.casefold() != place.casefold():
            return f"Drive from {origin} back to {place}, with the route and overnight stay forming the focus of the day."
        return f"Drive back to {place}, with the route and overnight stay forming the focus of the day."
    if profile_route_intro:
        return profile_route_intro
    if facts.has_travel:
        if facts.has_activity:
            return f"Return to {place}, with the onward route and included experience arranged together."
        return f"Return to {place}. The journey and arrival at your next stay are kept straightforward below."
    return f"Back in {place}, the day continues around the arrangements already confirmed for your stay."

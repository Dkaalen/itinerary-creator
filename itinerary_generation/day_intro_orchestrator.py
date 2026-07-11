"""Day-intro orchestration for client-facing itinerary copy."""

from __future__ import annotations

from itinerary_generation.common import get_primary_city, get_row_type, has_hotel, normalize_detail_level
from itinerary_generation.day_facts import build_day_facts
from itinerary_generation.day_group_tour_text import (
    _extract_group_tour_overview_start_time,
    _is_group_tour_start_day,
    _natural_group_tour_focus,
)
from itinerary_generation.day_activity_text import get_client_activity_phrase
from itinerary_generation.day_intent import classify_day_intent
from itinerary_generation.day_intro_writer import write_day_intro
from itinerary_generation.destination_copy import destination_stay_intro


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


def _city_stay_intro(day_rows, city, detail_level, visit_context):
    if has_hotel(day_rows):
        return destination_stay_intro(city, detail_level, rows=day_rows, visit_context=visit_context)
    if detail_level == "Elegant concise":
        return f"This is part of your stay in {city}, with arrangements listed below."
    if detail_level == "Rich descriptive":
        return f"This is part of your stay in {city}, with the day’s arrangements laid out clearly so the experience feels relaxed and easy to follow."
    return f"This is part of your stay in {city}, with arrangements included as listed below."


def create_day_intro(day_rows, detail_level="Standard client itinerary", *, visit_context=None):
    """Create a clear, client-facing day intro from day facts and intent."""

    detail_level = normalize_detail_level(detail_level)
    city = get_primary_city(day_rows)
    activities = [row for row in day_rows if get_row_type(row) == "Activity"]

    # Guided package start days have a separate factual group-tour model. Keep
    # that specialist path, then use the day brain for normal daywise copy.
    if _is_group_tour_start_day(day_rows):
        return _group_tour_start_intro(day_rows, activities, city or "the experience area")

    facts = build_day_facts(day_rows, visit_context=visit_context)
    intro = write_day_intro(facts, classify_day_intent(facts))
    if intro:
        return intro

    if city:
        return _city_stay_intro(day_rows, city, detail_level, visit_context)
    return "The day’s arrangements are listed below."


__all__ = ["create_day_intro"]

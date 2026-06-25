"""Activity-led day-intro helpers."""

from __future__ import annotations

from itinerary_generation.client_text_decisions import client_activity_intro, client_group_tour_intro


def _activity_day_intro(activity_title: str, city: str, source_text: str, detail_level: str = "") -> str:
    """Return deterministic client-facing intro text for an activity-led day."""

    return client_activity_intro(activity_title, city, source_text)


def _group_tour_intro(activity_title: str, city: str, source_text: str) -> str:
    """Return deterministic client-facing intro text for a group-tour day."""

    return client_group_tour_intro(activity_title, city, source_text)


def _activity_intro(title: str, city: str) -> str:
    """Return a short activity intro from title and city context."""

    return client_activity_intro(title, city)


def _group_tour_intro_from_source(title: str, source: str) -> str:
    """Return a group-tour intro when the source text is the main signal."""

    return client_group_tour_intro(title, "the route", source)


__all__ = [
    "_activity_day_intro",
    "_activity_intro",
    "_group_tour_intro",
    "_group_tour_intro_from_source",
]

"""Activity phrase helpers for day intro text."""

from __future__ import annotations

from itinerary_generation.titles import create_client_activity_title, normalize_client_day_title


def get_client_activity_phrase(row):
    title = create_client_activity_title(row) or row.get("title", "your included experience")
    return normalize_client_day_title(title, row) or title or "your included experience"


def _activity_phrase_with_city(activity_title, city_text):
    title = str(activity_title or "your included experience").strip()
    city = str(city_text or "").strip()
    if city and city.lower() in title.lower():
        return title
    return f"{title} in {city}" if city else title



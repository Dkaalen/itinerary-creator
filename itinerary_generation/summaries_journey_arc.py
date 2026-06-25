"""Build journey-arc chapter summaries."""

from __future__ import annotations

from itinerary_generation.common import get_day_number, get_primary_city, get_row_type
from itinerary_generation.summaries_experience import describe_city_experience


def format_day_range(days):
    if not days:
        return ""

    day_numbers = [get_day_number(day) for day in days]
    day_numbers = [number for number in day_numbers if number > 0]

    if not day_numbers:
        return "TBA"

    first_day = min(day_numbers)
    last_day = max(day_numbers)

    if first_day == last_day:
        return str(first_day)

    return f"{first_day} - {last_day}"

def create_journey_arc(grouped_days):
    chapters = []

    current_city = None
    current_days = []
    current_rows = []

    for day, rows in grouped_days.items():
        city = get_primary_city(rows)

        if not city:
            city = "Cruise" if any(get_row_type(row) == "Cruise" for row in rows) else "Journey"

        if current_city is None:
            current_city = city
            current_days = [day]
            current_rows = list(rows)

        elif city == current_city:
            current_days.append(day)
            current_rows.extend(rows)

        else:
            chapters.append({
                "chapter": current_city,
                "days": format_day_range(current_days),
                "experience": describe_city_experience(current_rows),
            })

            current_city = city
            current_days = [day]
            current_rows = list(rows)

    if current_city is not None:
        chapters.append({
            "chapter": current_city,
            "days": format_day_range(current_days),
            "experience": describe_city_experience(current_rows),
        })

    return chapters

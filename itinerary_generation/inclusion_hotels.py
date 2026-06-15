"""Accommodation and meal inclusion summary helpers."""

import re

from place_aliases import canonicalize_place_name
from text_polish import polish_hotel_name
from itinerary_generation.accommodation_inclusions import extract_stay_inclusions

from .inclusion_utils import clean


def format_meal_plan(meal_plan: str) -> str:
    meal = clean(meal_plan).lower()
    if not meal:
        return ""
    if meal == "breakfast and dinner":
        return "breakfast and dinner included"
    if meal == "breakfast":
        return "breakfast included"
    if meal == "dinner":
        return "dinner included"
    if meal in {"half board", "full board"}:
        return f"{meal} included"
    if meal == "room only":
        return "room only"
    if meal == "self catering":
        return "self-catering"
    if meal == "without breakfast":
        return "without breakfast"
    if "included" in meal:
        return meal
    return f"{meal} included"


def hotel_line(row: dict) -> str:
    raw_name = row.get("hotel_name") or row.get("title") or "Accommodation"
    name = polish_hotel_name(re.sub(r"^Accommodation\s*:\s*Check[- ]?in\s+at\s+", "", str(raw_name), flags=re.IGNORECASE))
    city = canonicalize_place_name(row.get("city", ""))
    nights = clean(row.get("hotel_nights", ""))
    room = clean(row.get("room_category", ""))
    meal = format_meal_plan(row.get("meal_plan", ""))
    star_rating = clean(row.get("star_rating", ""))

    title = name
    if star_rating and not re.search(r"\b[2-5]\s*[- ]?star\b", title, flags=re.IGNORECASE):
        title = f"{star_rating}-star {title}"
    if city:
        title += f", {city}"

    detail_sentences = []
    if nights:
        night_word = "night" if nights == "1" else "nights"
        detail_sentences.append(f"{nights} {night_word}")
    if room:
        detail_sentences.append(room)
    if meal:
        detail_sentences.append(meal.capitalize())

    detail_lines = []
    if detail_sentences:
        details = ". ".join(part.strip(" .") for part in detail_sentences if part.strip(" ."))
        if details and not details.endswith("."):
            details += "."
        detail_lines.append(details)

    stay_inclusions = extract_stay_inclusions(row)
    if stay_inclusions:
        detail_lines.append("Included with this stay:")
        detail_lines.extend(stay_inclusions)

    return title if not detail_lines else f"{title}\n" + "\n".join(detail_lines)


def has_non_breakfast_meal(meal: str) -> bool:
    lower = clean(meal).lower()
    return bool(lower and "breakfast" not in lower and "without" not in lower) or any(marker in lower for marker in ["dinner", "lunch", "full board", "half board", "full pension"])

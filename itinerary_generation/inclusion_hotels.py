"""Accommodation and meal inclusion summary helpers."""

from itinerary_generation.accommodation_brain import accommodation_brain_for_row
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


def _hotel_inclusion_label(row: dict) -> str:
    brain = accommodation_brain_for_row(row)
    label = brain.hotel_name or "Accommodation as listed"
    if brain.star_rating and f"{brain.star_rating}-star".lower() not in label.lower():
        label = f"{brain.star_rating}-star {label}"
    if brain.city and brain.city.lower() not in label.lower():
        label = f"{label}, {brain.city}"
    if "or similar" in row.get("details", "").lower() and "or similar" not in label.lower():
        label += " or similar"
    return label


def hotel_line(row: dict) -> str:
    brain = accommodation_brain_for_row(row)
    title = _hotel_inclusion_label(row)

    detail_sentences = []
    if brain.nights:
        detail_sentences.append(brain.nights)
    if brain.room_category:
        detail_sentences.append(brain.room_category)
    if brain.meal:
        detail_sentences.append(brain.meal.capitalize())

    detail_lines = []
    if detail_sentences:
        details = ". ".join(part.strip(" .") for part in detail_sentences if part.strip(" ."))
        if details and not details.endswith("."):
            details += "."
        detail_lines.append(details)

    stay_inclusions = [*extract_stay_inclusions(row), *(row.get("hotel_amenities") or [])]
    if stay_inclusions:
        detail_lines.append("Included with this stay:")
        detail_lines.extend(dict.fromkeys(stay_inclusions))

    return title if not detail_lines else f"{title}\n" + "\n".join(detail_lines)

def has_non_breakfast_meal(meal: str) -> bool:
    lower = clean(meal).lower()
    return bool(lower and "breakfast" not in lower and "without" not in lower) or any(marker in lower for marker in ["dinner", "lunch", "full board", "half board", "full pension"])

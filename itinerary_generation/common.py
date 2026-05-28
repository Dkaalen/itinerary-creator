import re
from collections import OrderedDict

from place_aliases import canonicalize_place_name, country_for_place, is_likely_service_text
from text_polish import polish_client_text

TRANSPORT_TYPES = ["Transport", "Train", "Flight", "Cruise", "Ferry"]

DETAIL_LEVELS = [
    "Elegant concise",
    "Standard client itinerary",
    "Rich descriptive",
]


def normalize_detail_level(value):
    value = str(value or "").strip()
    if value in DETAIL_LEVELS:
        return value
    return "Standard client itinerary"


def get_row_type(row):
    return row.get("effective_type") or row.get("type", "")


def get_day_number(day_text):
    digits = "".join(character for character in str(day_text) if character.isdigit())

    if digits:
        return int(digits)

    return 0


def group_rows_by_day(parsed_rows):
    grouped = {}

    for row in parsed_rows:
        if is_optional_row(row):
            continue

        day = row.get("day", "Unknown day")

        if day not in grouped:
            grouped[day] = []

        grouped[day].append(row)

    return OrderedDict(
        sorted(
            grouped.items(),
            key=lambda item: get_day_number(item[0]),
        )
    )


def get_day_count(grouped_days):
    return len(grouped_days)


def add_unique(items, item):
    clean_item = str(item or "").strip()

    if clean_item and clean_item not in items:
        items.append(clean_item)


def is_optional_row(row):
    return bool(row.get("is_optional"))


def main_rows_only(rows):
    return [row for row in rows if not is_optional_row(row)]


def optional_rows_only(rows):
    return [row for row in rows if is_optional_row(row)]


def is_valid_destination_city(city):
    city = canonicalize_place_name(str(city or "").strip())
    if not city:
        return False
    lower = city.lower()
    invalid_markers = [
        "private hotel",
        "private airport",
        "hotel to airport",
        "airport to hotel",
        "optional addon",
        "optional add",
        "optinal addon",
        "addon on request",
        "flight ",
    ]
    invalid_exact = {"accommodation", "hotel", "train", "flight", "cruise", "departure", "arrival"}
    if lower in invalid_exact:
        return False
    if any(re.search(pattern, lower) for pattern in [r"\bshower\b", r"\bsink\b", r"\bwc in carriage\b", r"\bbenefits\b", r"\bmade bed\b", r"women's", r"men's compartment"]):
        return False
    if is_likely_service_text(city):
        return False
    if any(marker in lower for marker in invalid_markers):
        return False
    if " to " in lower and any(word in lower for word in ["airport", "hotel", "station", "bergen", "copenhagen", "svol"]):
        return False
    return True


def clean_client_title(value):
    """Small client-facing title cleanup used after parsing."""

    title = str(value or "").strip()
    if not title:
        return ""

    # Remove over-marketing phrases that should not appear in polished itineraries.
    cleanup_phrases = [
        "with 97% Success Rate",
        "with Pro Photos Included",
        "with Pro Photographer",
        "with Professional Photographer",
        "Included",
    ]

    for phrase in cleanup_phrases:
        title = title.replace(phrase, "")

    title = title.replace("  ", " ").strip(" -:|")
    return title


def get_activity_text(row):
    return f'{row.get("original_title", "")} {row.get("title", "")} {row.get("details", "")}'.lower()


def has_hotel(day_rows):
    return any(get_row_type(row) == "Hotel" for row in day_rows)


def get_unique_cities(parsed_rows):
    cities = []

    for row in parsed_rows:
        if is_optional_row(row):
            continue

        city = canonicalize_place_name(row.get("city", "").strip())

        if is_valid_destination_city(city) and city not in cities:
            cities.append(city)

    return cities


def get_destination_countries(parsed_rows):
    """Return unique known countries represented by itinerary destination cities."""
    countries = []
    for city in get_unique_cities(parsed_rows):
        country = country_for_place(city)
        if country and country not in countries:
            countries.append(country)
    return countries


def has_self_drive_markers(parsed_rows):
    """Detect true rental-car/self-drive itinerary patterns.

    Do not treat ordinary self transfers, coach routes, supplier prose like
    "we drive", or scenic/return-drive day descriptions as self-drive. The
    itinerary should only be labelled self-drive when a rental vehicle/car is
    explicitly part of the arranged journey.
    """
    positive_markers = [
        "rental vehicle", "rental car", "rental suv", "pick up rental",
        "pickup rental", "drop vehicle", "drop off vehicle", "return vehicle",
        "car rental", "hire car",
    ]
    negative_markers = [
        "self transfer", "self-arranged", "self arranged", "coach", "bus",
        "flight", "train", "cruise", "ferry", "private transfer",
    ]
    for row in parsed_rows or []:
        text = f'{row.get("type", "")} {row.get("title", "")} {row.get("details", "")} {row.get("original_title", "")}'.lower()
        if any(marker in text for marker in positive_markers) and not ("self transfer" in text and "rental" not in text):
            return True
    return False


def is_self_arranged(row):
    text = f'{row.get("title", "")} {row.get("details", "")}'.lower()
    row_type = get_row_type(row)

    # Activity descriptions often contain exclusions like "guide not included"
    # or "food and drinks not included". Those should not turn the whole
    # experience into self-arranged travel.
    if row_type == "Activity":
        return False

    markers = [
        "self arranged",
        "self-arranged",
        "self arrnaged",
        "cost not included",
        "cost not inclueded",
        "price not included",
        "flight cost not",
    ]

    return any(marker in text for marker in markers)


def get_primary_city(day_rows):
    """
    Prefer the city of the main hotel/activity for mixed transfer days.
    This avoids days like Tromsø -> Bergen showing only the departure city.
    """

    if not day_rows:
        return ""

    priority_types = ["Hotel", "Flight", "Train", "Transport", "Cruise", "Ferry", "Activity", "Arrival", "Departure", "Transfer"]

    for preferred_type in priority_types:
        for row in day_rows:
            if get_row_type(row) == preferred_type:
                city = canonicalize_place_name(row.get("city", "").strip())
                if city and is_valid_destination_city(city):
                    return city

    return canonicalize_place_name(day_rows[0].get("city", "").strip())


def get_row_city(day_rows):
    city = get_primary_city(day_rows)
    return city or "the destination"

import re

import diagnostics
from text_polish import polish_client_text, polish_hotel_name
from parser_modules.common import clean_space
from parser_modules.details import extract_between_markers

def parse_meal_plan(value):
    text = clean_space(value)
    lower = text.lower()

    if not text:
        return ""

    # Important: detect exclusions before generic breakfast detection.
    if ("without" in lower or "no " in lower or "not included" in lower or "not incl" in lower) and ("breakfast" in lower or "brekafast" in lower):
        return "without breakfast"

    if "breakfast" in lower or "brekafast" in lower:
        if "dinner" in lower:
            return "breakfast and dinner"
        return "breakfast"

    if "half board" in lower or "half-board" in lower:
        return "half board"

    if "full board" in lower or "full-board" in lower:
        return "full board"

    if "room only" in lower:
        return "room only"

    if "self catering" in lower or "self-catering" in lower:
        return "self catering"

    if "dinner" in lower:
        return "dinner"

    return ""


def clean_room_category(value):
    room = clean_space(value)

    room = re.sub(r"^\d+\s*x\s*", "", room, flags=re.IGNORECASE)
    room = room.replace("Doubel", "Double").replace("doubel", "double")

    return clean_space(room)


_MEAL_PLAN_MARKERS = (
    "breakfast",
    "brekafast",
    "meal",
    "dinner",
    "half board",
    "full board",
    "room only",
    "self catering",
    "self-catering",
)

_COMMA_MEAL_PLAN_MARKERS = ("incl", *_MEAL_PLAN_MARKERS)

_ROOM_TYPE_MARKERS = ("room", "suite", "cabin")
_EXTENDED_LODGING_MARKERS = ("apartment", "villa", "cottage")
_ROOM_QUALIFIER_RE = re.compile(r"\b(premium|standard|aurora|glass|\d+\s*x)", re.IGNORECASE)
_BEDROOM_QUALIFIER_RE = re.compile(r"\b(\d+\s*x|one|two|three|four|five|bedroom)", re.IGNORECASE)
_ROOM_QUANTITY_RE = re.compile(r"\b\d+\s*x\s+", re.IGNORECASE)
_NIGHT_COUNT_RE = re.compile(r"(\d+)\s*(?:x\s*)?(?:night|nite|nt)s?", re.IGNORECASE)
_STAR_RATING_RE = re.compile(r"\b([2-5])\s*[- ]?star\b", re.IGNORECASE)


def _contains_any_marker(text, markers):
    return any(marker in text for marker in markers)


def _is_meal_plan_part(part_lower, *, comma_format=False):
    markers = _COMMA_MEAL_PLAN_MARKERS if comma_format else _MEAL_PLAN_MARKERS
    return _contains_any_marker(part_lower, markers)


def _is_room_like_part(part_lower):
    if _contains_any_marker(part_lower, _ROOM_TYPE_MARKERS):
        return True

    if "igloo" in part_lower and _ROOM_QUALIFIER_RE.search(part_lower):
        return True

    has_extended_lodging = _contains_any_marker(part_lower, _EXTENDED_LODGING_MARKERS)
    return bool(has_extended_lodging and _BEDROOM_QUALIFIER_RE.search(part_lower))


def _apply_room_part(part, hotel_name, room_category):
    quantity_match = _ROOM_QUANTITY_RE.search(part)
    if quantity_match and quantity_match.start() > 0 and not hotel_name:
        hotel_name = clean_space(part[:quantity_match.start()])
        room_category = room_category or clean_room_category(part[quantity_match.start():])
    else:
        room_category = room_category or clean_room_category(part)
    return hotel_name, room_category


def _split_embedded_room_quantity(hotel_name, room_category):
    split_match = _ROOM_QUANTITY_RE.search(hotel_name or "")
    if not split_match:
        return hotel_name, room_category

    before = clean_space(hotel_name[:split_match.start()])
    after = clean_space(hotel_name[split_match.start():])
    if before and after:
        return before, room_category or clean_room_category(after)

    return hotel_name, room_category


def _strip_hotel_prefix_from_room_category(hotel_name, room_category):
    if room_category and hotel_name and room_category.lower().startswith(hotel_name.lower()):
        return clean_room_category(clean_space(room_category[len(hotel_name):].strip(" ,-"))) or room_category
    return room_category


def parse_hotel_details(row, main_text, night_count_hint=""):
    """
    Parses accommodation details from both supported formats.

    Standard:
    Check in ... for a 2 night stay - Scandic Rovaniemi City - Standard Room - Breakfast included

    Colleague:
    3 Star , Hotel Arthur, 2xNight , 1xStandard Doubel Room, Incl Brekafast
    """

    text = clean_space(main_text)
    # Supplier accommodation rows often start with admin wording such as
    # "Accommodation: Check-in at Santa's Igloos". That wording is useful
    # to identify the row, but it should not become the hotel name or a day
    # title. Strip the admin prefix before hotel/room parsing.
    text = re.sub(r"^Accommodation\s*:\s*Check[- ]?in\s+at\s+", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"^Check[- ]?in\s+at\s+", "", text, flags=re.IGNORECASE).strip()
    lower = text.lower()

    hotel_name = ""
    nights = ""
    room_category = ""
    meal_plan = ""
    star_rating = ""

    star_match = _STAR_RATING_RE.search(text)
    if star_match:
        star_rating = star_match.group(1)

    if night_count_hint and str(night_count_hint).strip().isdigit():
        nights = str(night_count_hint).strip()

    match = re.search(r"for\s+a\s+(\d+)\s+(?:night|nite|nt)", lower)
    if match:
        nights = match.group(1)

    match = _NIGHT_COUNT_RE.search(lower)
    if match and not nights:
        nights = match.group(1)

    # Standard dash format.
    if " - " in text:
        parts = [clean_space(part) for part in text.split(" - ") if clean_space(part)]

        for part in parts:
            part_lower = part.lower()

            if "check in" in part_lower or "night stay" in part_lower:
                continue

            if _is_meal_plan_part(part_lower):
                meal_plan = parse_meal_plan(part)
                continue

            if _is_room_like_part(part_lower):
                hotel_name, room_category = _apply_room_part(part, hotel_name, room_category)
                continue

            if not hotel_name:
                hotel_name = part
            elif not room_category:
                room_category = clean_room_category(part)

    # Comma format.
    if not hotel_name or not room_category:
        comma_parts = [clean_space(part) for part in re.split(r",|\|", text) if clean_space(part)]

        for part in comma_parts:
            part_lower = part.lower()

            if _NIGHT_COUNT_RE.search(part_lower):
                continue

            if _STAR_RATING_RE.search(part_lower):
                # Keep the property name when a star rating is prefixed, e.g.
                # "3-star Hotel Arthur". Only the rating itself is metadata.
                cleaned_part = clean_space(_STAR_RATING_RE.sub("", part))
                if cleaned_part and not hotel_name:
                    hotel_name = cleaned_part
                continue

            if _is_meal_plan_part(part_lower, comma_format=True):
                meal_plan = meal_plan or parse_meal_plan(part)
                continue

            if _is_room_like_part(part_lower):
                hotel_name, room_category = _apply_room_part(part, hotel_name, room_category)
                continue

            if not hotel_name:
                hotel_name = part


    # Some supplier rows omit a comma between hotel name and room count, e.g.
    # "Fosshotel Glacier Lagoon 1x Standard Room - Triple". Treat the text
    # before the first room/count marker as the hotel name and the remainder as
    # the room category. This is a general hotel-pattern rule, not tied to one
    # specific property.
    hotel_name, room_category = _split_embedded_room_quantity(hotel_name, room_category)
    room_category = _strip_hotel_prefix_from_room_category(hotel_name, room_category)

    # If hotel name is missing in the text, avoid using the whole raw line.
    if hotel_name and any(marker in hotel_name.lower() for marker in ["check in", "night stay", "incl"]):
        hotel_name = ""

    hotel_name = polish_hotel_name(hotel_name)
    room_category = polish_client_text(room_category)
    meal_plan = polish_client_text(meal_plan)

    if not hotel_name:
        diagnostics.warn(
            "hotel_name_missing",
            f"Could not extract hotel name from: {text[:80]}",
            raw_value=text,
        )

    return {
        "hotel_name": hotel_name,
        "hotel_nights": nights,
        "room_category": room_category,
        "meal_plan": meal_plan,
        "star_rating": star_rating,
    }

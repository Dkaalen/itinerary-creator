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

    star_match = re.search(r"\b([2-5])\s*[- ]?star\b", text, flags=re.IGNORECASE)
    if star_match:
        star_rating = star_match.group(1)

    if night_count_hint and str(night_count_hint).strip().isdigit():
        nights = str(night_count_hint).strip()

    match = re.search(r"for\s+a\s+(\d+)\s+(?:night|nite|nt)", lower)
    if match:
        nights = match.group(1)

    match = re.search(r"(\d+)\s*(?:x\s*)?(?:night|nite|nt)s?", lower)
    if match and not nights:
        nights = match.group(1)

    # Standard dash format.
    if " - " in text:
        parts = [clean_space(part) for part in text.split(" - ") if clean_space(part)]

        for part in parts:
            part_lower = part.lower()

            if "check in" in part_lower or "night stay" in part_lower:
                continue

            if any(marker in part_lower for marker in ["breakfast", "brekafast", "meal", "dinner", "half board", "full board", "room only", "self catering", "self-catering"]):
                meal_plan = parse_meal_plan(part)
                continue

            room_like = (
                "room" in part_lower or "suite" in part_lower or "cabin" in part_lower
                or ("igloo" in part_lower and re.search(r"\b(premium|standard|aurora|glass|\d+\s*x)", part_lower))
                or (("apartment" in part_lower or "villa" in part_lower or "cottage" in part_lower) and re.search(r"\b(\d+\s*x|one|two|three|four|five|bedroom)", part_lower))
            )
            if room_like:
                quantity_match = re.search(r"\b\d+\s*x\s+", part, flags=re.IGNORECASE)
                if quantity_match and quantity_match.start() > 0 and not hotel_name:
                    hotel_name = clean_space(part[:quantity_match.start()])
                    room_category = room_category or clean_room_category(part[quantity_match.start():])
                else:
                    room_category = room_category or clean_room_category(part)
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

            if re.search(r"\d+\s*(?:x\s*)?(?:night|nite|nt)s?", part_lower):
                continue

            if re.search(r"\d+\s*[- ]?star", part_lower):
                # Keep the property name when a star rating is prefixed, e.g.
                # "3-star Hotel Arthur". Only the rating itself is metadata.
                cleaned_part = clean_space(re.sub(r"\b\d+\s*[- ]?star\b", "", part, flags=re.IGNORECASE))
                if cleaned_part and not hotel_name:
                    hotel_name = cleaned_part
                continue

            if any(marker in part_lower for marker in ["incl", "breakfast", "brekafast", "dinner", "half board", "full board", "room only", "self catering", "self-catering"]):
                meal_plan = meal_plan or parse_meal_plan(part)
                continue

            room_like = (
                "room" in part_lower or "suite" in part_lower or "cabin" in part_lower
                or ("igloo" in part_lower and re.search(r"\b(premium|standard|aurora|glass|\d+\s*x)", part_lower))
                or (("apartment" in part_lower or "villa" in part_lower or "cottage" in part_lower) and re.search(r"\b(\d+\s*x|one|two|three|four|five|bedroom)", part_lower))
            )
            if room_like:
                quantity_match = re.search(r"\b\d+\s*x\s+", part, flags=re.IGNORECASE)
                if quantity_match and quantity_match.start() > 0 and not hotel_name:
                    hotel_name = clean_space(part[:quantity_match.start()])
                    room_category = room_category or clean_room_category(part[quantity_match.start():])
                else:
                    room_category = room_category or clean_room_category(part)
                continue

            if not hotel_name:
                hotel_name = part


    # Some supplier rows omit a comma between hotel name and room count, e.g.
    # "Fosshotel Glacier Lagoon 1x Standard Room - Triple". Treat the text
    # before the first room/count marker as the hotel name and the remainder as
    # the room category. This is a general hotel-pattern rule, not tied to one
    # specific property.
    if hotel_name and re.search(r"\b\d+\s*x\s+", hotel_name, flags=re.IGNORECASE):
        split_match = re.search(r"\b\d+\s*x\s+", hotel_name, flags=re.IGNORECASE)
        before = clean_space(hotel_name[:split_match.start()])
        after = clean_space(hotel_name[split_match.start():])
        if before and after:
            hotel_name = before
            room_category = room_category or clean_room_category(after)

    if room_category and hotel_name and room_category.lower().startswith(hotel_name.lower()):
        room_category = clean_room_category(clean_space(room_category[len(hotel_name):].strip(" ,-"))) or room_category

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

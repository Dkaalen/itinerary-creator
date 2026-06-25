"""Parse and classify supplier room-category fragments."""

import re

from parser_modules.common import clean_space
from parser_modules.hotel_parser_meals import is_meal_plan_part

ROOM_TYPE_MARKERS = ("room", "suite", "cabin")
EXTENDED_LODGING_MARKERS = ("apartment", "villa", "cottage", "chalet", "studio", "igloo")
ROOM_QUALIFIER_RE = re.compile(r"\b(premium|standard|superior|classic|prime|double|twin|family|quad|large|small|aurora|glass|snowhotel|\d+\s*[x×])", re.IGNORECASE)
BEDROOM_QUALIFIER_RE = re.compile(r"\b(\d+\s*x|one|two|three|four|five|bedroom)", re.IGNORECASE)
ROOM_QUANTITY_RE = re.compile(r"\b\d+\s*[x×]\s*", re.IGNORECASE)
NIGHT_COUNT_RE = re.compile(r"(\d+)\s*(?:x\s*)?(?:night|nite|nt)s?", re.IGNORECASE)
STAR_RATING_RE = re.compile(r"\b([2-5](?:/[2-5])?)\s*[- ]?star\b", re.IGNORECASE)


def clean_room_category(value):
    room = re.sub(r"^\d+\s*[x×]\s*", "", clean_space(value), flags=re.IGNORECASE)
    room = room.replace("Doubel", "Double").replace("doubel", "double").replace("Cabinn", "Cabin").replace("cabinn", "cabin")
    room = re.split(r"\b(?:incl(?:uded)?|includes?|breakfast included|without breakfast|near station|distance from|hotel to station)\b", room, maxsplit=1, flags=re.IGNORECASE)[0]
    return clean_space(room.strip(" ,-"))


def is_room_like_part(part_lower):
    if re.search(r"\bhotel\b", part_lower) and not any(marker in part_lower for marker in ("room", "cabin", "cabinn", "suite", "igloo")) and not ROOM_QUANTITY_RE.search(part_lower): return False
    if "room" in part_lower or "cabin" in part_lower or "cabinn" in part_lower: return True
    if "bed" in part_lower and (ROOM_QUALIFIER_RE.search(part_lower) or ROOM_QUANTITY_RE.search(part_lower)): return True
    if ROOM_QUANTITY_RE.search(part_lower) and ROOM_QUALIFIER_RE.search(part_lower): return True
    if "suite" in part_lower and (ROOM_QUALIFIER_RE.search(part_lower) or ROOM_QUANTITY_RE.search(part_lower)): return True
    if "igloo" in part_lower and ROOM_QUALIFIER_RE.search(part_lower): return True
    return any(marker in part_lower for marker in EXTENDED_LODGING_MARKERS) and bool(BEDROOM_QUALIFIER_RE.search(part_lower) or ROOM_QUANTITY_RE.search(part_lower))


def apply_room_part(part, hotel_name, room_category):
    quantity = ROOM_QUANTITY_RE.search(part)
    if quantity and quantity.start() > 0 and not hotel_name: return clean_space(part[:quantity.start()]), room_category or clean_room_category(part[quantity.start():])
    return hotel_name, room_category or clean_room_category(part)


def split_embedded_room_quantity(hotel_name, room_category):
    match = ROOM_QUANTITY_RE.search(hotel_name or "")
    if not match: return hotel_name, room_category
    before, after = clean_space(hotel_name[:match.start()]), clean_space(hotel_name[match.start():])
    return (before, room_category or clean_room_category(after)) if before and after else (hotel_name, room_category)


def strip_hotel_prefix_from_room_category(hotel_name, room_category):
    if room_category and hotel_name and room_category.lower().startswith(hotel_name.lower()): return clean_room_category(clean_space(room_category[len(hotel_name):].strip(" ,-"))) or room_category
    return room_category


def name_before_night_count(part):
    match = NIGHT_COUNT_RE.search(part)
    if not match: return ""
    candidate = clean_space(STAR_RATING_RE.sub("", clean_space(part[:match.start()].strip(" ,-"))).strip(" ,-"))
    return "" if not candidate or is_room_like_part(candidate.lower()) or is_meal_plan_part(candidate.lower(), comma_format=True) else candidate


def room_after_night_count(part):
    match = NIGHT_COUNT_RE.search(part)
    if not match: return ""
    candidate = clean_space(part[match.end():].strip(" ,-"))
    return candidate if candidate and is_room_like_part(candidate.lower()) else ""

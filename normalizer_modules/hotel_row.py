"""Orchestrate normalization of a complete hotel row."""

import re

from normalizer_modules.hotel_dates import hotel_nights_from_date_range
from normalizer_modules.hotel_meals import extract_star_level, normalize_meal_plan
from normalizer_modules.hotel_names import clean_hotel_name_from_source, is_placeholder_hotel_name, strip_city_and_star_prefix
from normalizer_modules.hotel_rooms import extract_bed_type_from_source, extract_room_category_from_source, normalize_room_category
from normalizer_modules.text_utils import clean_space
from text_polish import polish_hotel_name


def normalize_hotel_row(row: dict) -> dict:
    source, city = clean_space(row.get("details", "")), clean_space(row.get("city", ""))
    star = extract_star_level(source) or clean_space(row.get("star_rating", ""))
    name = polish_hotel_name(strip_city_and_star_prefix(row.get("hotel_name", ""), city))
    if is_placeholder_hotel_name(name, city):
        detected = clean_hotel_name_from_source(row)
        name = detected if detected and not is_placeholder_hotel_name(detected, city) else (f"{star}-star hotel" if star else "Centrally located hotel")
    room = normalize_room_category(row.get("room_category", ""))
    source_room = extract_room_category_from_source(source)
    if source_room and (not room or " x " in source_room.lower() or "," in source_room): room = source_room
    if name == "Centrally located hotel" and (source_room or room) and re.search(r"\b(?:igloo|villa|cabin|apartment|cottage|lodge)\b", source_room or room, flags=re.IGNORECASE): name = "Accommodation"
    if not room: room = "Standard Double Room"
    bed_type = extract_bed_type_from_source(source)
    if bed_type and bed_type.lower() not in room.lower(): room = f"{room} - {bed_type}"
    nights = clean_space(row.get("hotel_nights", ""))
    date_nights = hotel_nights_from_date_range(row.get("start_date", ""), row.get("end_date", ""))
    if date_nights and (not nights or (nights == "1" and int(date_nights) > 1)): nights = date_nights
    elif not nights:
        match = re.search(r"\b(\d+)\s*(?:x\s*)?(?:night|ngiht|nite|nt)s?", source, flags=re.IGNORECASE)
        if match: nights = match.group(1)
    if city and name.lower().endswith(" city"): name = name[:-5].strip() or name
    name = re.sub(r"\bSariselka\b", "Saariselkä", name, flags=re.IGNORECASE)
    row.update(hotel_name=name, title=name, room_category=room, hotel_nights=nights, meal_plan=normalize_meal_plan(row.get("meal_plan", ""), source), star_rating=star)
    return row

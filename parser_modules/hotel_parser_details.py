"""Orchestrate extraction of structured hotel details from a supplier row."""

import re

import diagnostics
from parser_modules.common import clean_space
from parser_modules.hotel_parser_meals import is_meal_plan_part, parse_meal_plan
from parser_modules.hotel_parser_rooms import (
    NIGHT_COUNT_RE, ROOM_QUANTITY_RE, STAR_RATING_RE, apply_room_part, clean_room_category,
    is_room_like_part, name_before_night_count, room_after_night_count, split_embedded_room_quantity,
    strip_hotel_prefix_from_room_category,
)
from text_polish import polish_client_text, polish_hotel_name


def _generic_hotel_name(row, star_rating):
    city = clean_space(row.get("city", ""))
    if not city: return ""
    return f"{star_rating}-star hotel in {city}" if star_rating else f"Accommodation in {city}"


def _initial_metadata(text, night_count_hint):
    star_match, prestrip_night = STAR_RATING_RE.search(text), re.search(r"for\s+a\s+(\d+)\s+(?:night|nite|nt)", text, flags=re.IGNORECASE)
    star = star_match.group(1) if star_match else ""
    nights = str(night_count_hint).strip() if str(night_count_hint).strip().isdigit() else ""
    if prestrip_night: nights = prestrip_night.group(1)
    match = NIGHT_COUNT_RE.search(text.lower())
    if match and not nights: nights = match.group(1)
    return star, nights


def _parse_dash_parts(text, hotel_name, room_category, meal_plan):
    for part in [clean_space(item) for item in text.split(" - ") if clean_space(item)]:
        lower = part.lower()
        if "check in" in lower or "night stay" in lower: continue
        if is_room_like_part(lower):
            hotel_name, room_category = apply_room_part(part, hotel_name, room_category)
            if is_meal_plan_part(lower): meal_plan = meal_plan or parse_meal_plan(part)
        elif is_meal_plan_part(lower): meal_plan = parse_meal_plan(part)
        elif not hotel_name: hotel_name = part
        elif not room_category: room_category = clean_room_category(part)
    return hotel_name, room_category, meal_plan


def _parse_comma_parts(text, hotel_name, room_category, meal_plan, nights):
    for part in [clean_space(item) for item in re.split(r",|\|", text) if clean_space(item)]:
        lower = part.lower()
        night_match = NIGHT_COUNT_RE.search(lower)
        if night_match:
            nights = nights or night_match.group(1)
            hotel_name = hotel_name or name_before_night_count(part)
            after = room_after_night_count(part)
            if after and not room_category: room_category = clean_room_category(after)
        elif STAR_RATING_RE.search(lower):
            cleaned = clean_space(STAR_RATING_RE.sub("", part)); hotel_name = hotel_name or name_before_night_count(cleaned) or cleaned
        elif not hotel_name and ("snowhotel" in lower or re.search(r"\bhotel\b", lower)) and not ROOM_QUANTITY_RE.search(lower): hotel_name = part
        elif is_room_like_part(lower):
            hotel_name, room_category = apply_room_part(part, hotel_name, room_category)
            if is_meal_plan_part(lower, comma_format=True): meal_plan = meal_plan or parse_meal_plan(part)
        elif is_meal_plan_part(lower, comma_format=True): meal_plan = meal_plan or parse_meal_plan(part)
        elif not hotel_name: hotel_name = part
    return hotel_name, room_category, meal_plan, nights


def parse_hotel_details(row, main_text, night_count_hint=""):
    text = re.sub(r"(?<=[a-z])Check[- ]?in", " Check in", clean_space(main_text), flags=re.IGNORECASE)
    star_rating, nights = _initial_metadata(text, night_count_hint)
    text = re.sub(r"^Accommodation\s*:\s*Check[- ]?in\s+at\s+|^Check[- ]?in\s+at\s+", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"\s+Check[- ]?in\s+to\s+your\s+accommodation\s+for\s+a\s+\d+\s+(?:night|nite|nt)s?\s+stay\b", "", text, flags=re.IGNORECASE).strip()
    hotel_name = room_category = meal_plan = ""
    if " - " in text: hotel_name, room_category, meal_plan = _parse_dash_parts(text, hotel_name, room_category, meal_plan)
    if not hotel_name or not room_category: hotel_name, room_category, meal_plan, nights = _parse_comma_parts(text, hotel_name, room_category, meal_plan, nights)
    hotel_name, room_category = split_embedded_room_quantity(hotel_name, room_category)
    room_category = strip_hotel_prefix_from_room_category(hotel_name, room_category)
    if hotel_name and any(marker in hotel_name.lower() for marker in ("check in", "night stay", "incl")): hotel_name = ""
    if hotel_name and re.fullmatch(r"[-–—]?|[2-5](?:/[2-5])?\s*[- ]?star", hotel_name.strip(), flags=re.IGNORECASE): hotel_name = ""
    hotel_name, room_category, meal_plan = polish_hotel_name(hotel_name), polish_client_text(room_category), polish_client_text(meal_plan)
    hotel_name = hotel_name or _generic_hotel_name(row, star_rating)
    if not hotel_name: diagnostics.warn("hotel_name_missing", f"Could not extract hotel name from: {text[:80]}", raw_value=text)
    return {"hotel_name": hotel_name, "hotel_nights": nights, "room_category": room_category, "meal_plan": meal_plan, "star_rating": star_rating}

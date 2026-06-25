"""Public compatibility facade for hotel parsing."""

from parser_modules.hotel_parser_details import parse_hotel_details
from parser_modules.hotel_parser_meals import parse_meal_plan
from parser_modules.hotel_parser_rooms import clean_room_category

__all__ = ["clean_room_category", "parse_hotel_details", "parse_meal_plan"]

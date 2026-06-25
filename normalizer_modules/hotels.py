"""Public compatibility facade for hotel normalization."""

from normalizer_modules.hotel_dates import hotel_nights_from_date_range as _hotel_nights_from_date_range
from normalizer_modules.hotel_meals import extract_star_level, normalize_meal_plan
from normalizer_modules.hotel_names import clean_hotel_name_from_source, is_placeholder_hotel_name
from normalizer_modules.hotel_rooms import (
    _normalize_single_room_category,
    extract_bed_type_from_source,
    extract_room_category_from_source,
    normalize_room_category,
)
from normalizer_modules.hotel_row import normalize_hotel_row

__all__ = ["clean_hotel_name_from_source", "extract_bed_type_from_source", "extract_room_category_from_source", "extract_star_level", "is_placeholder_hotel_name", "normalize_hotel_row", "normalize_meal_plan", "normalize_room_category"]

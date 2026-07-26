"""Supported public API for parsing raw itinerary input.

The parser implementation lives in :mod:`parser_modules`.  Only the functions
listed in ``__all__`` are supported outside that package; lower-level helpers
remain private implementation details.
"""

from parser_modules.extractors import (
    extract_duration_from_description,
    extract_includes_from_description,
    extract_luggage_included,
    extract_meeting_point_from_description,
    extract_time_from_description,
)
from parser_modules.hotels import clean_room_category, parse_hotel_details, parse_meal_plan
from parser_modules.parser_main import parse_itinerary
from shared.text import clean_space
from shared.source_time_normalize import normalize_time_text

__all__ = (
    "clean_room_category",
    "clean_space",
    "extract_duration_from_description",
    "extract_includes_from_description",
    "extract_luggage_included",
    "extract_meeting_point_from_description",
    "extract_time_from_description",
    "normalize_time_text",
    "parse_hotel_details",
    "parse_itinerary",
    "parse_meal_plan",
)

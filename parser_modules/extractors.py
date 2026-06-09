"""Compatibility facade for parser field extractors.

The concrete extractor implementations live in focused modules so time,
duration, meeting-point and inclusion parsing can evolve independently.
"""

from parser_modules.extract_inclusions import extract_includes_from_description, extract_luggage_included
from parser_modules.extract_meeting_point import extract_meeting_point_from_description
from parser_modules.extract_time import extract_duration_from_description, extract_time_from_description

__all__ = [
    "extract_duration_from_description",
    "extract_includes_from_description",
    "extract_luggage_included",
    "extract_meeting_point_from_description",
    "extract_time_from_description",
]

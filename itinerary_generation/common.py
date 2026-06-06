"""Compatibility facade for common itinerary-generation helpers."""

from __future__ import annotations

from itinerary_generation.common_constants import DETAIL_LEVELS, TRANSPORT_TYPES, normalize_detail_level
from itinerary_generation.day_grouping import get_day_count, group_rows_by_day
from itinerary_generation.day_grouping_utils import get_day_number
from itinerary_generation.destination_helpers import (
    clean_client_title,
    destination_cities_for_row,
    get_destination_countries,
    get_display_destination_city,
    get_primary_city,
    get_row_city,
    get_unique_cities,
    is_valid_destination_city,
    overnight_destination_cities,
)
from itinerary_generation.group_tour_accommodation import (
    _add_group_tour_accommodation_rows,
    _extract_group_tour_accommodation_hints,
)
from itinerary_generation.row_filters import (
    add_unique,
    get_activity_text,
    get_row_type,
    has_hotel,
    has_self_drive_markers,
    get_commercial_status,
    is_commercially_included,
    is_optional_row,
    is_self_arranged,
    main_rows_only,
    optional_rows_only,
)

__all__ = [
    "DETAIL_LEVELS",
    "TRANSPORT_TYPES",
    "_add_group_tour_accommodation_rows",
    "_extract_group_tour_accommodation_hints",
    "add_unique",
    "clean_client_title",
    "get_activity_text",
    "get_day_count",
    "get_day_number",
    "destination_cities_for_row",
    "get_destination_countries",
    "get_display_destination_city",
    "get_primary_city",
    "get_row_city",
    "get_row_type",
    "get_unique_cities",
    "group_rows_by_day",
    "has_hotel",
    "has_self_drive_markers",
    "get_commercial_status",
    "is_commercially_included",
    "is_optional_row",
    "is_self_arranged",
    "is_valid_destination_city",
    "main_rows_only",
    "normalize_detail_level",
    "optional_rows_only",
    "overnight_destination_cities",
]

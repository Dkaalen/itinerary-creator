"""Compatibility wrapper for itinerary generation helpers.

The implementation is split across the itinerary_generation package. Existing
imports from generator.py are kept working through these re-exports.
"""

from itinerary_generation.common import (
    TRANSPORT_TYPES,
    DETAIL_LEVELS,
    normalize_detail_level,
    get_row_city,
    get_row_type,
    get_day_number,
    group_rows_by_day,
    get_day_count,
    add_unique,
    is_optional_row,
    main_rows_only,
    optional_rows_only,
    is_valid_destination_city,
    clean_client_title,
    get_activity_text,
    has_hotel,
    get_unique_cities,
    is_self_arranged,
    get_primary_city,
)
from itinerary_generation.transport import (
    has_airport_arrival_transfer,
    has_airport_departure_transfer,
    _route_destination_from_text,
    is_route_transfer,
    get_transfer_travel_title,
    get_primary_transport_title,
    has_only_departure_arrangements,
    get_first_transfer_title,
    has_self_arranged_transport,
    has_norway_in_a_nutshell,
    has_glass_igloo_or_arctic_resort,
)
from itinerary_generation.titles import (
    create_client_activity_title,
    create_trip_title,
    create_trip_subtitle,
    create_destinations_line,
    create_day_title,
)
from itinerary_generation.summaries import (
    create_trip_glance,
    describe_city_experience,
    format_day_range,
    create_journey_arc,
)
from itinerary_generation.day_text import (
    get_client_activity_phrase,
    create_day_intro,
    create_travel_route_label,
)
from itinerary_generation.inclusions import (
    sentence_case_transport_title,
    clean_include_item,
    format_transport_inclusion,
    create_whats_included,
    create_whats_not_included,
    create_final_note,
)

__all__ = [name for name in globals() if not name.startswith('__')]

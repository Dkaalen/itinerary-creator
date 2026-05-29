"""Compatibility facade for shared rendering helper functions."""

from __future__ import annotations

from ui.accommodation_display_helpers import meal_phrase, plural_nights
from ui.activity_description_helpers import (
    _BAD_DESCRIPTION_FALLBACK_MARKERS,
    _SUPPLIER_SECTION_LABEL_RE,
    _extract_section_after_label,
    _real_supplier_description,
    _strip_supplier_day_heading,
    _trim_description_sentences,
    get_activity_description,
)
from ui.activity_logistics import (
    clean_pickup_dropoff_value,
    detect_hotel_pickup_dropoff_text,
    get_activity_logistics,
)
from ui.render_text_helpers import (
    clean_space,
    esc,
    get_detail_level_name,
    list_to_text,
    normalize_list,
    render_list_items,
    text_to_list,
)
from ui.time_display import (
    display_time,
    display_time_with_duration,
    get_activity_duration_label,
    get_time_period,
)
from ui.transport_display_helpers import (
    is_self_arranged_transport,
    is_self_transfer,
    is_tallinn_ferry_day_trip,
)

__all__ = [
    "_BAD_DESCRIPTION_FALLBACK_MARKERS",
    "_SUPPLIER_SECTION_LABEL_RE",
    "_extract_section_after_label",
    "_real_supplier_description",
    "_strip_supplier_day_heading",
    "_trim_description_sentences",
    "clean_pickup_dropoff_value",
    "clean_space",
    "detect_hotel_pickup_dropoff_text",
    "display_time",
    "display_time_with_duration",
    "esc",
    "get_activity_description",
    "get_activity_duration_label",
    "get_activity_logistics",
    "get_detail_level_name",
    "get_time_period",
    "is_self_arranged_transport",
    "is_self_transfer",
    "is_tallinn_ferry_day_trip",
    "list_to_text",
    "meal_phrase",
    "normalize_list",
    "plural_nights",
    "render_list_items",
    "text_to_list",
]

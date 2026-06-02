"""Compatibility facade for inclusion and exclusion summary helpers.

Implementation lives in focused modules so flat legacy inclusions and structured
exclusions can evolve independently without coupling optional/self-arranged
logic to inclusion rendering.
"""

from itinerary_generation.inclusion_flat import (
    sentence_case_transport_title,
    clean_include_item,
    format_transport_inclusion,
    create_whats_included,
    create_final_note,
)
from itinerary_generation.exclusion_sections import (
    DEFAULT_WHATS_NOT_INCLUDED_ITEMS,
    commercial_row_title as _commercial_row_title,
    row_date_suffix as _row_date_suffix,
    specific_optional_items as _specific_optional_items,
    specific_self_arranged_items as _specific_self_arranged_items,
    create_specific_exclusion_sections,
    flatten_specific_exclusion_sections,
    create_whats_not_included,
)

__all__ = [
    "DEFAULT_WHATS_NOT_INCLUDED_ITEMS",
    "sentence_case_transport_title",
    "clean_include_item",
    "format_transport_inclusion",
    "create_whats_included",
    "create_whats_not_included",
    "create_final_note",
    "_commercial_row_title",
    "_row_date_suffix",
    "_specific_optional_items",
    "_specific_self_arranged_items",
    "create_specific_exclusion_sections",
    "flatten_specific_exclusion_sections",
]

"""Compatibility facade for what's-not-included section helpers."""

from __future__ import annotations

from itinerary_generation.exclusion_constants import DEFAULT_WHATS_NOT_INCLUDED_ITEMS, EXCLUSION_SECTION_ORDER
from itinerary_generation.exclusion_final_builder import (
    _commercial_rule_item,
    _default_exclusion_items,
    create_structured_whats_not_included,
    create_whats_not_included,
)
from itinerary_generation.exclusion_row_rules import (
    _commercial_reason,
    _commercial_status,
    _is_cost_not_included_row,
    _is_flight_row,
    _is_self_transfer_row,
    _is_transport_row,
    _rental_cost_not_included_label,
    _row_search_text,
    commercial_row_title,
    row_date_suffix,
    self_arranged_flight_notice,
)
from itinerary_generation.exclusion_source_items import (
    _row_specific_not_included_items,
    _specific_cost_not_included_label,
    _split_exclusion_phrases,
)
from itinerary_generation.exclusion_specific_sections import (
    _add_unique_structured,
    _row_id,
    _structured_item,
    create_source_aware_exclusion_sections,
    create_specific_exclusion_sections,
    flatten_specific_exclusion_sections,
    specific_optional_items,
    specific_self_arranged_items,
)

__all__ = (
    "DEFAULT_WHATS_NOT_INCLUDED_ITEMS",
    "EXCLUSION_SECTION_ORDER",
    "_row_id",
    "_structured_item",
    "_split_exclusion_phrases",
    "_row_specific_not_included_items",
    "_specific_cost_not_included_label",
    "_commercial_status",
    "_commercial_reason",
    "_row_search_text",
    "_is_self_transfer_row",
    "_is_flight_row",
    "_is_transport_row",
    "_is_cost_not_included_row",
    "_rental_cost_not_included_label",
    "row_date_suffix",
    "self_arranged_flight_notice",
    "commercial_row_title",
    "specific_self_arranged_items",
    "specific_optional_items",
    "create_specific_exclusion_sections",
    "_add_unique_structured",
    "create_source_aware_exclusion_sections",
    "flatten_specific_exclusion_sections",
    "_commercial_rule_item",
    "_default_exclusion_items",
    "create_structured_whats_not_included",
    "create_whats_not_included",
)

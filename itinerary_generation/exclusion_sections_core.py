"""Compatibility facade for :mod:`itinerary_generation.exclusion_sections`.

The implementation now lives in the responsibility-named module. This file
keeps legacy ``*_core`` imports working without becoming a catch-all again.
"""

from __future__ import annotations

from itinerary_generation.exclusion_sections import (
    DEFAULT_WHATS_NOT_INCLUDED_ITEMS,
    EXCLUSION_SECTION_ORDER,
    _row_id,
    _structured_item,
    _split_exclusion_phrases,
    _row_specific_not_included_items,
    _specific_cost_not_included_label,
    _commercial_status,
    _commercial_reason,
    _row_search_text,
    _is_self_transfer_row,
    _is_flight_row,
    _is_transport_row,
    _is_cost_not_included_row,
    _rental_cost_not_included_label,
    row_date_suffix,
    self_arranged_flight_notice,
    commercial_row_title,
    specific_self_arranged_items,
    specific_optional_items,
    create_specific_exclusion_sections,
    _add_unique_structured,
    create_source_aware_exclusion_sections,
    flatten_specific_exclusion_sections,
    _commercial_rule_item,
    _default_exclusion_items,
    create_structured_whats_not_included,
    create_whats_not_included,
)

__all__ = ('DEFAULT_WHATS_NOT_INCLUDED_ITEMS', 'EXCLUSION_SECTION_ORDER', '_row_id', '_structured_item', '_split_exclusion_phrases', '_row_specific_not_included_items', '_specific_cost_not_included_label', '_commercial_status', '_commercial_reason', '_row_search_text', '_is_self_transfer_row', '_is_flight_row', '_is_transport_row', '_is_cost_not_included_row', '_rental_cost_not_included_label', 'row_date_suffix', 'self_arranged_flight_notice', 'commercial_row_title', 'specific_self_arranged_items', 'specific_optional_items', 'create_specific_exclusion_sections', '_add_unique_structured', 'create_source_aware_exclusion_sections', 'flatten_specific_exclusion_sections', '_commercial_rule_item', '_default_exclusion_items', 'create_structured_whats_not_included', 'create_whats_not_included',)

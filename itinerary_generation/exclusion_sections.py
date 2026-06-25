"""Compatibility facade for What's-not-included helpers."""

from __future__ import annotations

from itinerary_generation.exclusion_sections_core import (
    DEFAULT_WHATS_NOT_INCLUDED_ITEMS,
    row_date_suffix,
    self_arranged_flight_notice,
    commercial_row_title,
    specific_self_arranged_items,
    specific_optional_items,
    create_specific_exclusion_sections,
    create_source_aware_exclusion_sections,
    flatten_specific_exclusion_sections,
    create_structured_whats_not_included,
    create_whats_not_included,
)

__all__ = ['DEFAULT_WHATS_NOT_INCLUDED_ITEMS', 'row_date_suffix', 'self_arranged_flight_notice', 'commercial_row_title', 'specific_self_arranged_items', 'specific_optional_items', 'create_specific_exclusion_sections', 'create_source_aware_exclusion_sections', 'flatten_specific_exclusion_sections', 'create_structured_whats_not_included', 'create_whats_not_included']

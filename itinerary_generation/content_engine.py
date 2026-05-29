"""Compatibility facade for client-facing itinerary content rules.

Focused helpers live in smaller modules so rendering/content behavior can be
changed and tested in safer slices. Import from this module remains supported.
"""

from __future__ import annotations

from itinerary_generation.activity_descriptions import (
    _description_from_included_items,
    client_activity_description,
    safe_generic_description,
)
from itinerary_generation.content_text import (
    _sentences,
    _trim_supplier_sections,
    clean_inline,
    row_text,
)
from itinerary_generation.display_text_safety import (
    is_internal_note_text,
    sanitize_day_intro,
    sanitize_display_text,
    sanitize_supplier_prose,
)
from itinerary_generation.inclusion_cleanup import (
    merge_compound_inclusions,
    sanitize_inclusion_item,
)
from itinerary_generation.supplier_text import (
    group_tour_pickup_window_from_overview,
    is_group_tour_overview,
    is_supplier_day_row,
    supplier_activity_body,
    supplier_day_body,
)
from itinerary_generation.title_cleanup import (
    RAW_SUPPLIER_MARKERS,
    TYPO_FIXES,
    _GENERIC_FALLBACK_MARKERS,
    clean_admin_title_fragment,
    clean_client_title,
    cleaned_generic_activity_title,
    has_raw_supplier_residue,
    looks_like_generated_fallback,
    repair_common_supplier_typos,
    strip_supplier_title_metadata,
)

__all__ = [
    "RAW_SUPPLIER_MARKERS",
    "TYPO_FIXES",
    "_GENERIC_FALLBACK_MARKERS",
    "_description_from_included_items",
    "_sentences",
    "_trim_supplier_sections",
    "clean_admin_title_fragment",
    "clean_client_title",
    "clean_inline",
    "cleaned_generic_activity_title",
    "client_activity_description",
    "group_tour_pickup_window_from_overview",
    "has_raw_supplier_residue",
    "is_group_tour_overview",
    "is_internal_note_text",
    "is_supplier_day_row",
    "looks_like_generated_fallback",
    "merge_compound_inclusions",
    "repair_common_supplier_typos",
    "row_text",
    "safe_generic_description",
    "sanitize_day_intro",
    "sanitize_display_text",
    "sanitize_inclusion_item",
    "sanitize_supplier_prose",
    "strip_supplier_title_metadata",
    "supplier_activity_body",
    "supplier_day_body",
]

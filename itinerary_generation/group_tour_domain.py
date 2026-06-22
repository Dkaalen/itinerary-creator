"""Public facade for canonical multi-day group-tour package contracts.

The group-tour implementation is split by responsibility so parser, preview,
editor, inclusion, and PDF consumers can share one stable public import path
without one oversized domain module.
"""

from __future__ import annotations

from itinerary_generation.group_tour_constants import (
    GROUP_TOUR_CANONICAL_FAMILY,
    GROUP_TOUR_CONTRACT_KIND,
    GROUP_TOUR_CONTRACT_VERSION,
    GROUP_TOUR_PRODUCT_TYPE,
)
from itinerary_generation.group_tour_models import (
    GroupTourAccommodationPolicy,
    GroupTourCommercialItem,
    GroupTourDay,
    GroupTourPackage,
)
from itinerary_generation.group_tour_builder import build_group_tour_package
from itinerary_generation.group_tour_master_rows import is_group_tour_master_row
from itinerary_generation.group_tour_serialization import (
    annotate_group_tour_rows,
    group_tour_day_from_row,
    group_tour_package_from_row,
)

# Compatibility imports for existing private-module tests and diagnostics. New
# code should import from the focused modules above instead.
from itinerary_generation.group_tour_accommodation_policy import _accommodation_policy, _policies
from itinerary_generation.group_tour_builder import _package_id
from itinerary_generation.group_tour_commercial_items import _commercial_item, _commercial_status
from itinerary_generation.group_tour_day_parser import (
    _accommodation_note,
    _apply_package_accommodation_hints,
    _build_day,
    _day_candidates,
    _day_highlights,
    _meal_markers,
    _overnight_area,
    _package_day_accommodation_hints,
    _package_day_parts,
    _route_points,
    _sentences_with_markers,
    _source_attractions,
)
from itinerary_generation.group_tour_master_rows import (
    _group_style,
    _master_candidates,
    _master_description,
    _master_inclusions,
    _master_title,
    _package_pickup_time,
)
from itinerary_generation.group_tour_row_helpers import (
    _group_tour_day_source,
    _itinerary_day_number,
    _row_text,
    _row_type,
    _source_row_id,
)
from itinerary_generation.group_tour_text import (
    _clean,
    _clean_strings,
    _field,
    _infer_season,
    _int,
    _normalize_season,
    _number_text,
    _section,
)

__all__ = [
    "GROUP_TOUR_CANONICAL_FAMILY",
    "GROUP_TOUR_CONTRACT_KIND",
    "GROUP_TOUR_CONTRACT_VERSION",
    "GROUP_TOUR_PRODUCT_TYPE",
    "GroupTourAccommodationPolicy",
    "GroupTourCommercialItem",
    "GroupTourDay",
    "GroupTourPackage",
    "annotate_group_tour_rows",
    "build_group_tour_package",
    "group_tour_day_from_row",
    "group_tour_package_from_row",
    "is_group_tour_master_row",
]

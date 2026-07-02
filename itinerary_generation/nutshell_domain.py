"""Compatibility facade for the Norway in a Nutshell product contract."""

from __future__ import annotations

from itinerary_generation.nutshell_cleaning import _clean_place, _clean_places, _clean_strings
from itinerary_generation.nutshell_constants import (
    NUTSHELL_CANONICAL_FAMILY,
    NUTSHELL_CONTRACT_KIND,
    NUTSHELL_CONTRACT_VERSION,
    NUTSHELL_PRODUCT_NAME,
    NUTSHELL_PRODUCT_TYPE,
)
from itinerary_generation.nutshell_journey_builder import (
    _client_title,
    _source_row_ids,
    attach_nutshell_journey,
    build_nutshell_journey,
    has_nutshell_journey,
    nutshell_journey_from_row,
    resolve_nutshell_journey,
)
from itinerary_generation.nutshell_model import NutshellJourney, NutshellLeg
from itinerary_generation.nutshell_parsing import is_source_backed_nutshell_route_package
from itinerary_generation.nutshell_route_parser import (
    _direct_route_endpoints,
    _direction,
    _legs_from_points,
    _mapping_legs,
    _mode_from_supplier_item,
    _ordered_points_from_legs,
    _supplier_legs,
    _title_endpoints,
)
from itinerary_generation.nutshell_source import _activity_product, _row_source, is_nutshell_row

__all__ = [
    "NUTSHELL_CANONICAL_FAMILY",
    "NUTSHELL_CONTRACT_KIND",
    "NUTSHELL_CONTRACT_VERSION",
    "NUTSHELL_PRODUCT_NAME",
    "NUTSHELL_PRODUCT_TYPE",
    "NutshellJourney",
    "NutshellLeg",
    "_activity_product",
    "_clean_place",
    "_clean_places",
    "_clean_strings",
    "_client_title",
    "_direct_route_endpoints",
    "_direction",
    "_legs_from_points",
    "_mapping_legs",
    "_mode_from_supplier_item",
    "_ordered_points_from_legs",
    "_row_source",
    "_source_row_ids",
    "_supplier_legs",
    "_title_endpoints",
    "attach_nutshell_journey",
    "build_nutshell_journey",
    "has_nutshell_journey",
    "is_nutshell_row",
    "is_source_backed_nutshell_route_package",
    "nutshell_journey_from_row",
    "resolve_nutshell_journey",
]

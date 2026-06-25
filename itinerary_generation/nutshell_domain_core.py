"""Compatibility facade for :mod:`itinerary_generation.nutshell_domain`.

The implementation now lives in the responsibility-named module. This file
keeps legacy ``*_core`` imports working without becoming a catch-all again.
"""

from __future__ import annotations

from itinerary_generation.nutshell_domain import (
    NUTSHELL_CANONICAL_FAMILY,
    NUTSHELL_PRODUCT_NAME,
    NUTSHELL_PRODUCT_TYPE,
    NUTSHELL_CONTRACT_KIND,
    NUTSHELL_CONTRACT_VERSION,
    NutshellLeg,
    NutshellJourney,
    _clean_place,
    _clean_strings,
    _clean_places,
    _row_source,
    _activity_product,
    is_nutshell_row,
    _title_endpoints,
    _direct_route_endpoints,
    _mode_from_supplier_item,
    _supplier_legs,
    _mapping_legs,
    _legs_from_points,
    _ordered_points_from_legs,
    _direction,
    _source_row_ids,
    _client_title,
    build_nutshell_journey,
    nutshell_journey_from_row,
    resolve_nutshell_journey,
    has_nutshell_journey,
    attach_nutshell_journey,
)

__all__ = ('NUTSHELL_CANONICAL_FAMILY', 'NUTSHELL_PRODUCT_NAME', 'NUTSHELL_PRODUCT_TYPE', 'NUTSHELL_CONTRACT_KIND', 'NUTSHELL_CONTRACT_VERSION', 'NutshellLeg', 'NutshellJourney', '_clean_place', '_clean_strings', '_clean_places', '_row_source', '_activity_product', 'is_nutshell_row', '_title_endpoints', '_direct_route_endpoints', '_mode_from_supplier_item', '_supplier_legs', '_mapping_legs', '_legs_from_points', '_ordered_points_from_legs', '_direction', '_source_row_ids', '_client_title', 'build_nutshell_journey', 'nutshell_journey_from_row', 'resolve_nutshell_journey', 'has_nutshell_journey', 'attach_nutshell_journey',)

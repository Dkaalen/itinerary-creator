"""Compatibility facade for the Norway in a Nutshell product contract."""

from __future__ import annotations

from itinerary_generation.nutshell_domain_core import (
    NUTSHELL_CANONICAL_FAMILY,
    NUTSHELL_CONTRACT_KIND,
    NUTSHELL_CONTRACT_VERSION,
    NUTSHELL_PRODUCT_NAME,
    NUTSHELL_PRODUCT_TYPE,
    NutshellJourney,
    NutshellLeg,
    attach_nutshell_journey,
    build_nutshell_journey,
    has_nutshell_journey,
    is_nutshell_row,
    nutshell_journey_from_row,
    resolve_nutshell_journey,
)

__all__ = ['NUTSHELL_CANONICAL_FAMILY', 'NUTSHELL_CONTRACT_KIND', 'NUTSHELL_CONTRACT_VERSION', 'NUTSHELL_PRODUCT_NAME', 'NUTSHELL_PRODUCT_TYPE', 'NutshellJourney', 'NutshellLeg', 'attach_nutshell_journey', 'build_nutshell_journey', 'has_nutshell_journey', 'is_nutshell_row', 'nutshell_journey_from_row', 'resolve_nutshell_journey']

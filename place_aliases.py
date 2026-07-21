"""Compatibility facade for the Nordic place alias database."""

from __future__ import annotations

from place_alias_data import PLACES, SERVICE_PHRASES
from place_alias_maps import (
    ALIAS_PATTERNS,
    ALIAS_RECORDS,
    ALIAS_TO_CANONICAL,
    ALIAS_TO_PLACES,
    CANONICAL_PLACES,
    CANONICAL_TO_COUNTRY,
    CANONICAL_TO_KIND,
    _build_alias_maps,
    _build_alias_patterns,
)
from place_alias_queries import (
    canonicalize_place_name,
    countries_for_place,
    country_for_place,
    is_known_place,
    is_likely_service_text,
    kind_for_place,
    normalize_place_text,
)
from place_alias_text import _key, _strip_accents, normalize_place_key

__all__ = [
    "ALIAS_PATTERNS",
    "ALIAS_RECORDS",
    "ALIAS_TO_CANONICAL",
    "ALIAS_TO_PLACES",
    "CANONICAL_PLACES",
    "CANONICAL_TO_COUNTRY",
    "CANONICAL_TO_KIND",
    "PLACES",
    "SERVICE_PHRASES",
    "_build_alias_maps",
    "_build_alias_patterns",
    "_key",
    "_strip_accents",
    "canonicalize_place_name",
    "countries_for_place",
    "country_for_place",
    "is_known_place",
    "is_likely_service_text",
    "kind_for_place",
    "normalize_place_key",
    "normalize_place_text",
]

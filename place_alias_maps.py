"""Precomputed lookup maps for Nordic place aliases."""

from __future__ import annotations

import re

from place_alias_data import PLACES
from place_alias_text import normalize_place_key


def _build_alias_maps():
    alias_to_canonical: dict[str, str] = {}
    alias_to_places: dict[str, list[tuple[str, str, str]]] = {}
    alias_records: list[tuple[str, str]] = []

    for place in PLACES:
        canonical = place["canonical"]
        country = str(place.get("country", ""))
        kind = str(place.get("kind", ""))
        aliases = [canonical] + list(place.get("aliases", []))
        for alias in aliases:
            if not alias:
                continue
            key = normalize_place_key(alias)
            record = (country, canonical, kind)
            if key and key not in alias_to_canonical:
                alias_to_canonical[key] = canonical
            if key and record not in alias_to_places.setdefault(key, []):
                alias_to_places[key].append(record)
            alias_records.append((str(alias), canonical))

    alias_records = sorted(set(alias_records), key=lambda item: len(item[0]), reverse=True)
    return alias_to_canonical, {key: tuple(values) for key, values in alias_to_places.items()}, alias_records


ALIAS_TO_CANONICAL, ALIAS_TO_PLACES, ALIAS_RECORDS = _build_alias_maps()


def _build_alias_patterns():
    patterns = []
    common_word_aliases = {"are", "in", "to", "on", "at", "by"}
    for alias, canonical in ALIAS_RECORDS:
        if alias == canonical:
            continue
        alias_key = normalize_place_key(alias)
        if alias_key in common_word_aliases:
            continue
        canonical_key = normalize_place_key(canonical)
        suffix_key = canonical_key[len(alias_key):].strip() if canonical_key.startswith(alias_key) else ""
        escaped = re.escape(alias)
        pattern = re.compile(rf"(?<![\wÀ-ÿ]){escaped}(?![\wÀ-ÿ])", flags=re.IGNORECASE)
        patterns.append((pattern, canonical, suffix_key))
    return patterns


ALIAS_PATTERNS = _build_alias_patterns()
CANONICAL_PLACES = {place["canonical"] for place in PLACES}
CANONICAL_TO_COUNTRY = {place["canonical"]: place["country"] for place in PLACES}
CANONICAL_TO_KIND = {place["canonical"]: place.get("kind", "") for place in PLACES}

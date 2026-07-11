"""Public place alias lookup and normalization helpers."""

from __future__ import annotations

import re
from functools import lru_cache

from place_alias_data import SERVICE_PHRASES
from place_alias_maps import ALIAS_PATTERNS, ALIAS_TO_CANONICAL, ALIAS_TO_PLACES, CANONICAL_PLACES, CANONICAL_TO_COUNTRY, CANONICAL_TO_KIND
from place_alias_text import _key


@lru_cache(maxsize=4096)
def canonicalize_place_name(value: str, country_hint: str = "") -> str:
    text = str(value or "").strip(" .,-|:")
    if not text:
        return ""

    records = ALIAS_TO_PLACES.get(_key(text), ())
    hint = _key(country_hint)
    if hint:
        for country, canonical, _kind in records:
            if _key(country) == hint:
                return canonical
    canonical = ALIAS_TO_CANONICAL.get(_key(text))
    return canonical or text


def is_known_place(value: str) -> bool:
    return canonicalize_place_name(value) in CANONICAL_PLACES


def countries_for_place(value: str) -> tuple[str, ...]:
    """Return every country supported by a canonical or alias value."""

    countries = {country for country, _canonical, _kind in ALIAS_TO_PLACES.get(_key(value), ()) if country}
    return tuple(sorted(countries))


def country_for_place(value: str, country_hint: str = "") -> str:
    """Return a country without silently guessing across ambiguous aliases."""

    countries = countries_for_place(value)
    if country_hint:
        hint = _key(country_hint)
        return next((country for country in countries if _key(country) == hint), "")
    if len(countries) == 1:
        return countries[0]
    return ""


def kind_for_place(value: str, country_hint: str = "") -> str:
    """Return the place kind for a known alias, optionally country-qualified."""

    records = ALIAS_TO_PLACES.get(_key(value), ())
    hint = _key(country_hint)
    if hint:
        records = tuple(record for record in records if _key(record[0]) == hint)
    kinds = {kind for _country, _canonical, kind in records if kind}
    if len(kinds) == 1:
        return next(iter(kinds))
    canonical = canonicalize_place_name(value, country_hint)
    return CANONICAL_TO_KIND.get(canonical, "") if not records else ""


def is_likely_service_text(value: str) -> bool:
    text = _key(value)
    if not text:
        return False
    if any(phrase in text for phrase in [_key(item) for item in SERVICE_PHRASES]):
        return True
    if " to " in f" {text} " and any(word in text for word in ["airport", "hotel", "station", "accommodation"]):
        return True
    return False


def normalize_place_text(value: str) -> str:
    """Replace known place aliases inside free text while preserving other text.

    Keep this public wrapper permissive for legacy non-string callers. The
    normalized string-only core is safe to cache.
    """

    return _normalize_place_text_cached(str(value or ""))


@lru_cache(maxsize=8192)
def _normalize_place_text_cached(text: str) -> str:
    if not text:
        return text

    text = text.replace("–", "-").replace("—", "-")

    for pattern, canonical, suffix_key in ALIAS_PATTERNS:
        def replace_alias(match, canonical=canonical, suffix_key=suffix_key):
            # Preserve meaningful supplier aliases when they are already shown
            # as explanatory parentheticals after the canonical name, e.g.
            # "Preikestolen (Pulpit Rock)" must not become
            # "Preikestolen (Preikestolen)".
            preceding = text[max(0, match.start() - len(canonical) - 12): match.start()]
            if canonical.lower().startswith("mount ") and re.search(r"\bMount\s+$", preceding, flags=re.IGNORECASE):
                return match.group(0)
            if re.search(rf"{re.escape(canonical)}\s*\(\s*$", preceding, flags=re.IGNORECASE):
                return match.group(0)
            if suffix_key:
                following = text[match.end(): match.end() + len(suffix_key) + 8]
                if _key(following).startswith(suffix_key):
                    return match.group(0)
            return canonical

        text = pattern.sub(replace_alias, text)

    text = re.sub(r"\b(National Park)(?:\s+\1)+\b", r"\1", text, flags=re.IGNORECASE)

    return text

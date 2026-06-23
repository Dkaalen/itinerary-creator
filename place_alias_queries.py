"""Public place alias lookup and normalization helpers."""

from __future__ import annotations

import re
from functools import lru_cache

from place_alias_data import SERVICE_PHRASES
from place_alias_maps import ALIAS_PATTERNS, ALIAS_TO_CANONICAL, CANONICAL_PLACES, CANONICAL_TO_COUNTRY, CANONICAL_TO_KIND
from place_alias_text import _key


@lru_cache(maxsize=4096)
def canonicalize_place_name(value: str) -> str:
    text = str(value or "").strip(" .,-|:")
    if not text:
        return ""

    canonical = ALIAS_TO_CANONICAL.get(_key(text))
    return canonical or text


def is_known_place(value: str) -> bool:
    return canonicalize_place_name(value) in CANONICAL_PLACES


def country_for_place(value: str) -> str:
    """Return the country for a known canonical or alias place."""
    return CANONICAL_TO_COUNTRY.get(canonicalize_place_name(value), "")


def kind_for_place(value: str) -> str:
    """Return the place kind for a known canonical or alias place."""
    return CANONICAL_TO_KIND.get(canonicalize_place_name(value), "")


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

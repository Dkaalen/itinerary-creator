"""Compose client-facing activity descriptions from supplier facts."""

from __future__ import annotations

import re

from place_aliases import canonicalize_place_name
from text_polish import polish_client_text, strip_price_fragments

from itinerary_generation.description_facts import _has_bad_residue
from itinerary_generation.description_patterns import GENERATED_INTRO_PATTERNS
from itinerary_generation.description_schema import DescriptionDraft
from itinerary_generation.description_sources import _clean_inline, _is_group_day, _narrative_source, _title, explicit_description_source
from itinerary_generation.description_templates import (
    _compose_group_day,
    _compose_known_activity,
    _fallback_description,
)


def compose_activity_description(row: dict, fallback: str = "") -> DescriptionDraft:
    """Return a freshly composed client-facing description.

    The returned text is intentionally new prose derived from facts. It should
    not be a direct supplier paragraph unless the source is already short,
    clean and client-ready.
    """

    title = _title(row)
    city = canonicalize_place_name(row.get("city", ""))
    source = _narrative_source(row)
    warnings: list[str] = []

    explicit_description = explicit_description_source(row)
    if explicit_description and not _has_bad_residue(explicit_description):
        return DescriptionDraft(text=explicit_description, source="explicit_description", warnings=warnings)

    if _is_group_day(row):
        text = _compose_group_day(row, source, title, city)
        return DescriptionDraft(text=text, source="composed_group_day", warnings=warnings)

    text = _compose_known_activity(row, source, title, city)
    if not text and fallback:
        # Keep fallback only if it is already clean and specific. Otherwise compose generic.
        fb = polish_client_text(_clean_inline(strip_price_fragments(fallback)))
        if fb and not _has_bad_residue(fb) and not any(re.search(p, fb, re.I) for p in GENERATED_INTRO_PATTERNS):
            # Still keep short and polished.
            sentences = re.split(r"(?<=[.!?])\s+", fb)
            text = polish_client_text(" ".join(sentences[:2]))
            warnings.append("clean_fallback_used")
    if not text:
        text = _fallback_description(row, title, city)
        warnings.append("generic_composed_fallback")

    if _has_bad_residue(text):
        warnings.append("supplier_residue_removed")
        text = _fallback_description(row, title, city)
    return DescriptionDraft(text=polish_client_text(text), source="composed_activity", warnings=warnings)

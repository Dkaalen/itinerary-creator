"""Compose client-facing activity descriptions from supplier facts."""

from __future__ import annotations

import re

from place_aliases import canonicalize_place_name
from text_polish import polish_client_text, strip_price_fragments

from itinerary_generation.activity_location_contract import activity_location_facts
from itinerary_generation.activity_training_catalogue import catalogue_description_for_row
from itinerary_generation.description_facts import _has_bad_residue
from itinerary_generation.description_patterns import GENERATED_INTRO_PATTERNS
from itinerary_generation.description_schema import DescriptionDraft
from itinerary_generation.description_sources import _clean_inline, _is_group_day, _narrative_source, _title, explicit_description_source
from itinerary_generation.description_templates import (
    _compose_group_day,
    _compose_known_activity,
    _fallback_description,
)


def _clean_specific_fallback(fallback: str) -> str:
    """Return a short clean fallback, or ``""`` when it is not client-ready."""

    if not fallback:
        return ""
    fb = polish_client_text(_clean_inline(strip_price_fragments(fallback)))
    if not fb or _has_bad_residue(fb):
        return ""
    if any(re.search(pattern, fb, re.I) for pattern in GENERATED_INTRO_PATTERNS):
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", fb)
    return polish_client_text(" ".join(sentence.strip() for sentence in sentences[:2] if sentence.strip()))


def _fallback_is_more_location_specific(*, text: str, fallback: str, base_city: str, excursion_region: str) -> bool:
    """Prefer clean location-contract prose over generic base-city wording.

    Known-activity descriptions are normally stronger than broad fallbacks,
    but a generic keyword rule must not say an excursion is simply "in" the
    overnight base when the parser/location contract has a more specific
    region-level truth available.
    """

    if not text or not fallback or not base_city or not excursion_region:
        return False
    text_l = text.casefold()
    fallback_l = fallback.casefold()
    base_l = base_city.casefold()
    region_l = excursion_region.casefold()
    base_city_claim = f"in {base_l}" in text_l
    region_missing = region_l not in text_l
    fallback_has_region = region_l in fallback_l
    return base_city_claim and region_missing and fallback_has_region


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

    # Product-specific templates are intentionally evaluated before the
    # training catalogue.  The catalogue is example-backed and useful, but it
    # must not override stronger domain templates such as icebreaker product
    # names, ice-floating wording, Sámi/reindeer wording, or Bergen foot-and-
    # boat phrasing.
    text = _compose_known_activity(row, source, title, city)
    clean_fallback = _clean_specific_fallback(fallback)
    location_facts = activity_location_facts(row, title=title, city=city, source_text=source)
    if _fallback_is_more_location_specific(
        text=text,
        fallback=clean_fallback,
        base_city=location_facts.base_city,
        excursion_region=location_facts.excursion_region,
    ):
        text = clean_fallback
        warnings.append("location_specific_fallback_used")

    if not text:
        catalogue_description = catalogue_description_for_row(row)
        if catalogue_description and not _has_bad_residue(catalogue_description):
            return DescriptionDraft(text=catalogue_description, source="training_catalogue", warnings=warnings)
    if not text and clean_fallback:
        text = clean_fallback
        warnings.append("clean_fallback_used")
    if not text:
        text = _fallback_description(row, title, city)
        warnings.append("generic_composed_fallback")

    if _has_bad_residue(text):
        warnings.append("supplier_residue_removed")
        text = _fallback_description(row, title, city)
    return DescriptionDraft(text=polish_client_text(text), source="composed_activity", warnings=warnings)

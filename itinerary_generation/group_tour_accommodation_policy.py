"""Accommodation and included-service policy extraction for group tours."""

from __future__ import annotations

import re
from typing import Sequence

from itinerary_generation.group_tour_models import GroupTourAccommodationPolicy, GroupTourDay
from itinerary_generation.group_tour_text import _clean_strings

def _accommodation_policy(
    source: str,
    inclusions: Sequence[str],
    duration_days: int,
    day_segments: Sequence[GroupTourDay],
) -> GroupTourAccommodationPolicy:
    wording = _clean_strings(
        item
        for item in inclusions
        if re.search(r"\b(hotel|guesthouse|accommodation|private bathroom|breakfast)\b", item, re.I)
    )
    day_notes = _clean_strings(day.accommodation_note for day in day_segments if day.accommodation_note)
    combined = "\n".join((source, *wording, *day_notes))
    lower = combined.casefold()
    included = bool(
        re.search(r"\b(hotel|guesthouse|accommodation|hotel stays?)\b", lower)
        and not re.search(r"\b(accommodation|hotel)\s+not\s+included\b", lower)
    )
    explicit_nights = re.search(r"\b(\d+)\s+nights?\b", combined, flags=re.I)
    nights = int(explicit_nights.group(1)) if explicit_nights else (max(0, duration_days - 1) if included else 0)
    nights_inferred = bool(included and nights and not explicit_nights)
    room_basis = ""
    if "sharing room basis" in lower or "shared room basis" in lower:
        room_basis = "Sharing room basis"
    elif "double room" in lower:
        room_basis = "Double room"
    elif "standard room" in lower:
        room_basis = "Standard room"
    bathroom = "Private bathroom" if "private bathroom" in lower else ""
    meal_plan = "Breakfast included" if "breakfast" in lower else ""
    exact_properties_confirmed = bool(
        included
        and re.search(r"\b(?:hotel|guesthouse)\s+[A-ZÁÉÍÓÚÝÞÆÖ]", combined)
        and not re.search(r"\b(or similar|subject to availability|countryside hotel|hotel stays?)\b", combined, re.I)
    )
    warnings: list[str] = []
    if nights_inferred:
        warnings.append("accommodation_nights_inferred_from_package_duration")
    if included and not wording and not day_notes:
        warnings.append("accommodation_policy_lacks_source_wording")
    return GroupTourAccommodationPolicy(
        included=included,
        nights=nights,
        nights_inferred=nights_inferred,
        room_basis=room_basis,
        bathroom=bathroom,
        meal_plan=meal_plan,
        exact_properties_confirmed=exact_properties_confirmed,
        source_wording=_clean_strings((*wording, *day_notes)),
        warnings=tuple(warnings),
    )


def _policies(inclusions: Sequence[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    transport = _clean_strings(
        item
        for item in inclusions
        if re.search(r"\b(pick[- ]?up|drop[- ]?off|transport|transfer|minibus|vehicle|coach|wifi)\b", item, re.I)
    )
    guide = _clean_strings(item for item in inclusions if re.search(r"\bguide|guidance\b", item, re.I))
    return transport, guide

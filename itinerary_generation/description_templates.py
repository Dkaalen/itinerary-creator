"""Template builders for composed activity descriptions."""

from __future__ import annotations

import re

from place_aliases import canonicalize_place_name
from text_polish import polish_client_text

from itinerary_generation.description_facts import (
    _extract_inclusion_facts,
    _extract_landmarks,
    _focus_from_title,
    _join,
)
from itinerary_generation.description_sources import _row_source
from itinerary_generation.description_known_activity_rules import match_known_activity_description
from itinerary_generation.product_rules import find_product_match


def _compose_group_day(row: dict, source: str, title: str, city: str) -> str:
    places = _extract_landmarks(source, limit=8)
    focus = _focus_from_title(title)
    region = canonicalize_place_name(row.get("city", "")) or city or "the region"
    full = f"{title} {source}".lower()

    if "whale" in full:
        place_list = _join(places, max_items=6) if places else "North Iceland"
        return polish_client_text(
            f"Combine the included whale watching experience with {place_list}, "
            "before the route carries on towards the next overnight stop or back to Reykjavík."
        )

    if places:
        place_list = _join(places, max_items=6)
        if "golden circle" in full:
            return polish_client_text(f"Begin the guided route with the Golden Circle, including {place_list}, before continuing to the first overnight stop outside Reykjavík.")
        if "south coast" in full or "katla" in full:
            return polish_client_text(f"Follow the South Coast through {place_list}, combining waterfall scenery, black-sand coastline and the day’s included ice-cave experience where listed.")
        if "jökuls" in full or "jokuls" in full or "diamond beach" in full or "skaftafell" in full:
            return polish_client_text(f"Spend the day among Iceland’s glacier landscapes, with {place_list} included along the route towards the next overnight area.")
        if "eastfjord" in full or "egils" in full:
            return polish_client_text(f"Travel through the Eastfjords, where {place_list} give the day a quieter, more local feel before the overnight stop.")
        if "north iceland" in full or "mývatn" in full or "myvatn" in full or "dettifoss" in full:
            return polish_client_text(f"Cross into North Iceland with stops around {place_list}, linking waterfalls, geothermal areas and northern landscapes in one guided day.")
        return polish_client_text(f"Travel through {region} with your guide, with {place_list} shaping the day’s main stops before the overnight arrangements.")
    return polish_client_text(
        f"Travel with your guide through {region}, with the day focused on {focus} before continuing to your overnight stay."
    )


def _compose_known_activity(row: dict, source: str, title: str, city: str) -> str:
    landmark_source = " ".join([
        source,
        " ".join(row.get("includes", []) or []),
        " ".join(row.get("notable_sights", []) or []),
    ])
    full = f"{title} {landmark_source}".lower()
    places = _extract_landmarks(landmark_source, limit=8)
    inclusions = _extract_inclusion_facts(row, limit=4)
    city_phrase = f" in {city}" if city and city.lower() not in title.lower() else ""

    product_match = find_product_match(row, title, source)
    if product_match and product_match.description:
        return product_match.description

    return match_known_activity_description(
        row=row,
        title=title,
        city=city,
        full=full,
        places=places,
        inclusions=inclusions,
        city_phrase=city_phrase,
    )

def _fallback_description(row: dict, title: str, city: str) -> str:
    city_phrase = f" in {city}" if city and city.lower() not in title.lower() else ""
    lower = f"{title} {_row_source(row)}".lower()
    if "train" in lower or "rail" in lower:
        return polish_client_text(f"Continue by rail towards {city or 'your next destination'}, with the route and timing arranged as part of the day.")
    if "transfer" in lower or "self" in lower:
        return polish_client_text(f"Today’s travel arrangements{city_phrase} are kept clear and easy to follow, giving you a smooth transition to the next part of the journey.")
    return polish_client_text(f"Enjoy {title}{city_phrase}, with the schedule arranged to keep the experience clear, comfortable and easy to follow.")



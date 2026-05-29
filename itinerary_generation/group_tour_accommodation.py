"""Synthetic accommodation rows inferred from group-tour overview text."""

from __future__ import annotations

import re

from place_aliases import canonicalize_place_name
from text_polish import polish_client_text
from itinerary_generation.day_grouping_utils import get_day_number
from itinerary_generation.destination_helpers import get_primary_city
from itinerary_generation.row_filters import get_row_type


def _add_group_tour_accommodation_rows(grouped):
    """Add placeholder overnight rows for supplier group-tour accommodation.

    Guided/group-tour supplier overviews often say things like
    ``Day 2–3: West Iceland guesthouse w/breakfast`` without giving a named
    property. That is still important client information, so we represent it as
    a lightweight hotel row for the relevant itinerary day instead of losing it.
    The logic is generic: it reads numbered overnight ranges from the group-tour
    overview and maps supplier day 1 to the itinerary day containing the
    overview row.
    """

    if not grouped:
        return

    existing_keys = set()
    for rows in grouped.values():
        for row in rows:
            if get_row_type(row) == "Hotel":
                existing_keys.add((row.get("day"), canonicalize_place_name(row.get("city", "")).lower()))

    for day, rows in list(grouped.items()):
        day_number = get_day_number(day)
        if not day_number:
            continue
        for overview in rows:
            if get_row_type(overview) != "Day Overview":
                continue
            overview_text = f'{overview.get("title", "")}\n{overview.get("details", "")}\n{overview.get("original_title", "")}'
            if not re.search(r"\b(group\s+tour|holiday\s+package|sharing\s+room\s+basis)\b", overview_text, flags=re.IGNORECASE):
                continue
            for accommodation in _extract_group_tour_accommodation_hints(overview_text):
                target_day_number = day_number + accommodation["start_day"] - 1
                target_day = f"Day {target_day_number}"
                if target_day not in grouped:
                    continue
                city_source = accommodation["city"]
                if not city_source and accommodation["name"].lower() != "countryside guesthouse accommodation":
                    city_source = get_primary_city(grouped[target_day]) or overview.get("city", "")
                city = canonicalize_place_name(city_source)
                key = (target_day, city.lower())
                if key in existing_keys:
                    continue
                grouped[target_day].append({
                    "day": target_day,
                    "type": "Hotel",
                    "effective_type": "Hotel",
                    "city": city,
                    "title": accommodation["name"],
                    "hotel_name": accommodation["name"],
                    "hotel_nights": "1",
                    "room_category": "",
                    "meal_plan": "breakfast" if accommodation["breakfast"] else "",
                    "details": accommodation["raw"],
                    "original_title": accommodation["raw"],
                    "row_id": f"group_tour_hotel_{target_day_number}_{abs(hash(accommodation['raw'])) % 100000}",
                    "is_group_tour_accommodation": True,
                })
                existing_keys.add(key)


def _extract_group_tour_accommodation_hints(text):
    hints = []
    for raw_line in str(text or "").replace("–", "-").splitlines():
        line = polish_client_text(raw_line).strip(" •-*\t")
        if not line:
            continue
        match = re.match(r"^Day\s+(\d+)\s*-\s*(\d+)\s*:\s*(.+)$", line, flags=re.IGNORECASE)
        if not match:
            continue
        description = match.group(3).strip(" .")
        lower = description.lower()
        if not any(marker in lower for marker in ["hotel", "guesthouse", "accommodation", "lodge", "resort"]):
            continue
        city = description
        city = re.sub(r"\bw\s*/\s*breakfast\b|\bwith\s+breakfast\b|\bbreakfast\s+included\b", "", city, flags=re.IGNORECASE)
        city = re.sub(r"\b(?:hotel|guesthouse|accommodation|lodge|resort)\b", "", city, flags=re.IGNORECASE)
        city = city.strip(" ,-:")
        if "countryside" in lower:
            name = "Countryside guesthouse accommodation"
            city = ""
        elif "guesthouse" in lower:
            name = "Guesthouse accommodation"
        elif "hotel" in lower:
            name = "Hotel accommodation"
        else:
            name = "Accommodation"
        hints.append({
            "start_day": int(match.group(1)),
            "end_day": int(match.group(2)),
            "city": city,
            "name": name,
            "breakfast": bool(re.search(r"breakfast|w\s*/\s*breakfast|b/fast", description, flags=re.IGNORECASE)),
            "raw": description,
        })
    return hints

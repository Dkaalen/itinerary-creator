"""Extract and attach package accommodation placeholders."""

import re
from copy import deepcopy
from typing import Iterable

from itinerary_generation.group_tour_detection import is_group_tour_overview
from itinerary_generation.group_tour_supplier_titles import clean_group_tour_text, day_number
from itinerary_generation.day_grouping_utils import get_day_number
from itinerary_generation.destination_helpers import get_primary_city
from itinerary_generation.row_filters import get_row_type
from place_aliases import canonicalize_place_name
from text_polish import polish_client_text


def _normalise_phrase(raw: str) -> tuple[str, str, str]:
    text = clean_group_tour_text(raw).strip(" .:-")
    text = re.sub(r"\bw\s*/\s*breakfast\b", "with breakfast", text, flags=re.IGNORECASE)
    meal = "breakfast" if "breakfast" in text.lower() else ""
    text = re.sub(r"\bwith breakfast\b", "", text, flags=re.IGNORECASE).strip(" ,.-")
    lower = text.lower()
    kind = "guesthouse accommodation" if "guesthouse" in lower else "hotel accommodation" if "hotel" in lower else "accommodation"
    place = polish_client_text(re.sub(r"\b(?:hotel|guesthouse|accommodation)\b", "", text, flags=re.IGNORECASE).strip(" ,.-"))
    city = canonicalize_place_name(place) if place else ""
    if place and place.lower().startswith("countryside"): return "Countryside guesthouse accommodation", "", meal
    return kind[:1].upper() + kind[1:], city, meal


def extract_group_tour_accommodation_stays(rows: Iterable[dict]) -> list[dict]:
    stays, seen = [], set()
    for row in rows or []:
        if not is_group_tour_overview(row): continue
        source = str(row.get("details") or row.get("original_title") or row.get("title") or "").replace("–", "-").replace("—", "-")
        for raw in source.splitlines():
            line = clean_group_tour_text(raw).strip(" •-*|:")
            match = re.match(r"Day\s*(\d+)\s*(?:-\s*(\d+))?\s*:\s*(.+)$", line, flags=re.IGNORECASE)
            if not match or not re.search(r"\b(hotel|guesthouse|accommodation)\b", match.group(3), flags=re.IGNORECASE): continue
            start, end, description = int(match.group(1)), int(match.group(2) or match.group(1)), clean_group_tour_text(match.group(3))
            hotel, city, meal = _normalise_phrase(description); key = (start, hotel.lower(), city.lower())
            if key in seen: continue
            seen.add(key); stays.append({"supplier_day": start, "supplier_end_day": end, "hotel_name": hotel, "city": city, "meal_plan": meal, "source_text": description})
    return stays


def add_group_tour_accommodation_rows(rows: list[dict]) -> list[dict]:
    updated = [deepcopy(row) for row in rows or []]; stays = extract_group_tour_accommodation_stays(updated)
    if not stays: return updated
    base = min([day_number(row.get("day", "")) for row in updated if is_group_tour_overview(row) and day_number(row.get("day", ""))] or [1])
    existing = {(day_number(row.get("day", "")), clean_group_tour_text(row.get("hotel_name") or row.get("title")).lower(), clean_group_tour_text(row.get("city")).lower()) for row in updated if (row.get("effective_type") or row.get("type")) == "Hotel"}
    synthetic = []
    for stay in stays:
        number = base + int(stay["supplier_day"]) - 1; hotel, city = stay["hotel_name"], stay["city"]; key = (number, hotel.lower(), city.lower())
        if key in existing: continue
        synthetic.append({"raw": stay.get("source_text", ""), "line_number": 0, "row_id": f"group-accommodation-{number}-{len(synthetic)+1}", "is_optional": False, "is_group_tour_accommodation": True, "day": f"Day {number}", "type": "Hotel", "effective_type": "Hotel", "start_date": "", "end_date": "", "city": city, "title": hotel, "original_title": hotel, "details": stay.get("source_text", ""), "time": "", "duration": "", "meeting_point": "", "end_point": "", "notable_sights": [], "includes": [], "luggage_included": "", "hotel_name": hotel, "hotel_nights": "1", "room_category": "", "meal_plan": stay.get("meal_plan", "")})
        existing.add(key)
    combined = updated + synthetic
    combined.sort(key=lambda row: (day_number(row.get("day", "")), 1 if row.get("is_group_tour_accommodation") else 0, int(row.get("line_number") or 0)))
    return combined


def _extract_group_tour_accommodation_hints(text):
    """Extract legacy day-range accommodation hints from an overview."""
    hints = []
    for raw_line in str(text or "").replace("–", "-").splitlines():
        line = polish_client_text(raw_line).strip(" •-*\t")
        match = re.match(r"^Day\s+(\d+)\s*-\s*(\d+)\s*:\s*(.+)$", line, flags=re.IGNORECASE)
        if not match: continue
        description = match.group(3).strip(" ."); lower = description.lower()
        if not any(marker in lower for marker in ("hotel", "guesthouse", "accommodation", "lodge", "resort")): continue
        city = re.sub(r"\b(?:hotel|guesthouse|accommodation|lodge|resort)\b", "", re.sub(r"\bw\s*/\s*breakfast\b|\bwith\s+breakfast\b|\bbreakfast\s+included\b", "", description, flags=re.IGNORECASE), flags=re.IGNORECASE).strip(" ,-:")
        if "countryside" in lower: name, city = "Countryside guesthouse accommodation", ""
        elif "guesthouse" in lower: name = "Guesthouse accommodation"
        elif "hotel" in lower: name = "Hotel accommodation"
        else: name = "Accommodation"
        hints.append({"start_day": int(match.group(1)), "end_day": int(match.group(2)), "city": city, "name": name, "breakfast": bool(re.search(r"breakfast|w\s*/\s*breakfast|b/fast", description, flags=re.IGNORECASE)), "raw": description})
    return hints


def _add_group_tour_accommodation_rows(grouped):
    """Attach legacy placeholder hotels to an already grouped day mapping."""
    if not grouped: return
    existing = {(row.get("day"), canonicalize_place_name(row.get("city", "")).lower()) for rows in grouped.values() for row in rows if get_row_type(row) == "Hotel"}
    for day, rows in list(grouped.items()):
        number = get_day_number(day)
        if not number: continue
        for overview in rows:
            if get_row_type(overview) != "Day Overview" or overview.get("group_tour_package") or overview.get("group_tour_role") == "package_master": continue
            text = f'{overview.get("title", "")}\n{overview.get("details", "")}\n{overview.get("original_title", "")}'
            if not re.search(r"\b(group\s+tour|holiday\s+package|sharing\s+room\s+basis)\b", text, flags=re.IGNORECASE): continue
            for item in _extract_group_tour_accommodation_hints(text):
                target_number = number + item["start_day"] - 1; target = f"Day {target_number}"
                if target not in grouped: continue
                city_source = item["city"]
                if not city_source and item["name"].lower() != "countryside guesthouse accommodation": city_source = get_primary_city(grouped[target]) or overview.get("city", "")
                city = canonicalize_place_name(city_source); key = (target, city.lower())
                if key in existing: continue
                grouped[target].append({"day": target, "type": "Hotel", "effective_type": "Hotel", "city": city, "title": item["name"], "hotel_name": item["name"], "hotel_nights": "1", "room_category": "", "meal_plan": "breakfast" if item["breakfast"] else "", "details": item["raw"], "original_title": item["raw"], "row_id": f"group_tour_hotel_{target_number}_{abs(hash(item['raw'])) % 100000}", "is_group_tour_accommodation": True})
                existing.add(key)

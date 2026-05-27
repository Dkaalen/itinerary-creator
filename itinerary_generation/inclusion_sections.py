"""Categorized, client-facing inclusion summaries.

These helpers build the final inclusion page from parsed itinerary rows rather
than broad generic bullets. The functions are deterministic and presentation
focused; they do not change parser data.
"""

from __future__ import annotations

import re
from collections import OrderedDict

from place_aliases import canonicalize_place_name
from text_polish import polish_hotel_name, polish_inclusion_item, polish_title

from itinerary_generation.common import TRANSPORT_TYPES, get_row_type, is_self_arranged, main_rows_only
from itinerary_generation.transport import get_transfer_travel_title, is_route_transfer
from itinerary_generation.titles import create_client_activity_title


def _clean(value: str) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


def _clean_multiline(value: str) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    if "\n" not in text:
        return _clean(text)
    lines = [_clean(line) for line in text.split("\n") if _clean(line)]
    return "\n".join(lines)


def _add_unique(items: list[str], item: str) -> None:
    clean_item = _clean_multiline(item)
    if clean_item and clean_item not in items:
        items.append(clean_item)

def _format_meal_plan(meal_plan: str) -> str:
    meal = _clean(meal_plan).lower()
    if not meal:
        return ""
    if meal == "breakfast and dinner":
        return "breakfast and dinner included"
    if meal == "breakfast":
        return "breakfast included"
    if meal == "dinner":
        return "dinner included"
    if meal == "without breakfast":
        return "without breakfast"
    if "included" in meal:
        return meal
    return f"{meal} included"


def _join_detail_parts(parts: list[str]) -> str:
    clean_parts = [_clean(part).strip(" ,") for part in parts if _clean(part).strip(" ,")]
    if not clean_parts:
        return ""
    if len(clean_parts) == 1:
        return clean_parts[0]
    return ", ".join(clean_parts[:-1]) + f" and {clean_parts[-1]}"


def _hotel_line(row: dict) -> str:
    name = polish_hotel_name(row.get("hotel_name") or row.get("title") or "Accommodation")
    city = canonicalize_place_name(row.get("city", ""))
    nights = _clean(row.get("hotel_nights", ""))
    room = _clean(row.get("room_category", ""))
    meal = _format_meal_plan(row.get("meal_plan", ""))

    title = name
    if city:
        title += f", {city}"

    detail_sentences = []
    if nights:
        night_word = "night" if nights == "1" else "nights"
        detail_sentences.append(f"{nights} {night_word}")
    if room:
        detail_sentences.append(room)
    if meal:
        detail_sentences.append(meal.capitalize())

    if not detail_sentences:
        return title

    details = ". ".join(part.strip(" .") for part in detail_sentences if part.strip(" ."))
    if details and not details.endswith("."):
        details += "."
    return f"{title}\n{details}"


def _activity_line(row: dict) -> str:
    title = create_client_activity_title(row) or row.get("title", "")
    return polish_title(title)


def _clean_transport_title(row: dict) -> str:
    row_type = get_row_type(row)
    title = _clean(row.get("title", ""))
    details = _clean(row.get("details", ""))
    combined = f"{title} {details}".lower()

    if row_type == "Transfer":
        if is_route_transfer(row):
            return get_transfer_travel_title(row)
        if "private" in combined and "airport" in combined and ("hotel" in combined or "accommodation" in combined):
            city = canonicalize_place_name(row.get("city", ""))
            return f"Private transfer from {city} Airport to your accommodation" if city else "Private airport transfer to your accommodation"
        return polish_title(title or "Private transfer")

    if row_type in TRANSPORT_TYPES:
        return polish_title(title or get_transfer_travel_title(row))

    return polish_title(title)


def _transport_bucket(row: dict) -> str:
    text = f'{row.get("title", "")} {row.get("details", "")}'.lower()
    row_type = get_row_type(row)
    if "private" in text:
        return "Private transfers"
    if row_type == "Train" or "train" in text:
        return "Rail journeys"
    if row_type == "Flight" or "flight" in text:
        return "Flights"
    if row_type in {"Cruise", "Ferry"} or "ferry" in text or "cruise" in text:
        return "Ferries & cruises"
    if "coach" in text or "bus" in text:
        return "Coach transfers"
    return "Other arranged transport"


def _transport_line(row: dict) -> str:
    title = _clean_transport_title(row)
    extras = []
    for item in row.get("includes", []) or []:
        item = polish_inclusion_item(item, title)
        lower = item.lower()
        if lower in {"tickets included", "ticket included"}:
            if "coach" in title.lower() or "bus" in title.lower():
                item = "coach ticket included"
            elif "train" in title.lower():
                item = "train ticket included"
            else:
                item = "ticket included"
        if item and item.lower() not in title.lower():
            _add_unique(extras, item)
    luggage = polish_inclusion_item(row.get("luggage_included", ""), title)
    if luggage:
        _add_unique(extras, luggage)
    if extras:
        detail = _join_detail_parts(extras).strip(" .")
        if detail:
            detail = detail[:1].upper() + detail[1:]
            return f"{title}\n{detail}."
    return title


def _guide_support_items(activity_rows: list[dict]) -> list[str]:
    items: list[str] = []
    for row in activity_rows:
        title = _activity_line(row)
        include_text = " ".join(str(item or "") for item in (row.get("includes", []) or [])).lower()
        detail_text = f'{row.get("details", "")} {row.get("original_title", "")}'.lower()
        text = f"{include_text} {detail_text}"
        if any(marker in text for marker in ["guide", "guiding", "driver & guide", "driver and guide"]):
            _add_unique(items, f"Guide service for {title}")
        if "professional camera" in text or "camera pictures" in text or "photos" in text:
            _add_unique(items, f"Photo support for {title}")
        if "pick" in text and "drop" in text and "transfer" in text:
            _add_unique(items, f"Local activity transfers for {title}")
    return items


def create_categorized_inclusions(parsed_rows, grouped_days=None) -> list[dict]:
    """Return inclusion sections as [{title, items}]."""

    rows = main_rows_only(parsed_rows)
    sections: list[dict] = []

    hotel_items: list[str] = []
    activity_items: list[str] = []
    transport_buckets: OrderedDict[str, list[str]] = OrderedDict()
    meal_items: list[str] = []

    hotel_rows = [row for row in rows if get_row_type(row) == "Hotel"]
    activity_rows = [row for row in rows if get_row_type(row) == "Activity"]

    for row in hotel_rows:
        _add_unique(hotel_items, _hotel_line(row))
        meal = _format_meal_plan(row.get("meal_plan", ""))
        city = canonicalize_place_name(row.get("city", ""))
        name = polish_hotel_name(row.get("hotel_name") or row.get("title") or "accommodation")
        if meal and "without" not in meal:
            _add_unique(meal_items, f"{meal.capitalize()} at {name}{', ' + city if city else ''}")

    for row in activity_rows:
        _add_unique(activity_items, _activity_line(row))

    for row in rows:
        row_type = get_row_type(row)
        if row_type not in set(TRANSPORT_TYPES) | {"Transfer"}:
            continue
        if is_self_arranged(row):
            continue
        line = _transport_line(row)
        if not line:
            continue
        bucket = _transport_bucket(row)
        transport_buckets.setdefault(bucket, [])
        _add_unique(transport_buckets[bucket], line)

    if hotel_items:
        sections.append({"title": "Accommodation", "items": hotel_items})
    if activity_items:
        sections.append({"title": "Activities & experiences", "items": activity_items})
    for bucket, items in transport_buckets.items():
        if items:
            sections.append({"title": bucket, "items": items})
    if meal_items:
        sections.append({"title": "Meals included", "items": meal_items})

    support_items = _guide_support_items(activity_rows)
    if support_items:
        sections.append({"title": "Guides & local support", "items": support_items})

    return sections


def flatten_inclusion_sections(sections: list[dict]) -> list[str]:
    items: list[str] = []
    for section in sections or []:
        title = _clean(section.get("title", ""))
        if title:
            items.append(f"{title}:")
        for item in section.get("items", []) or []:
            items.append(item)
    return items

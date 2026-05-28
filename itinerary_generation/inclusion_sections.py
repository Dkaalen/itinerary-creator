"""Categorized, client-facing inclusion summaries.

These helpers build the final inclusion page from parsed itinerary rows rather
than broad generic bullets. The functions are deterministic and presentation
focused; they do not change parser data.
"""

from __future__ import annotations

import re
from collections import OrderedDict

from parser_modules.common import extract_route_points
from place_aliases import canonicalize_place_name
from text_polish import polish_hotel_name, polish_inclusion_item, polish_title

from itinerary_generation.common import TRANSPORT_TYPES, get_row_type, is_self_arranged, main_rows_only, has_self_drive_markers
from itinerary_generation.transport import get_transfer_travel_title, is_route_transfer, get_premium_transport_phrase
from itinerary_generation.titles import create_client_activity_title, normalize_client_day_title
from itinerary_generation.content_engine import sanitize_inclusion_item, merge_compound_inclusions, clean_client_title


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


def _is_self_transfer_row(row: dict) -> bool:
    text = f'{row.get("title", "")} {row.get("details", "")}'.lower()
    return get_row_type(row) == "Transfer" and "self transfer" in text


def _is_cruise_leisure_row(row: dict) -> bool:
    text = f'{row.get("title", "")} {row.get("details", "")}'.lower()
    return get_row_type(row) == "Cruise" and "leisure" in text and "cruise" in text


def _is_cruise_arrival_row(row: dict) -> bool:
    text = f'{row.get("title", "")} {row.get("details", "")}'.lower()
    return get_row_type(row) == "Cruise" and "arrival" in text


def _route_transport_line(row: dict) -> str:
    row_type = get_row_type(row)
    # Private/self/local transfers should keep their standardized transfer
    # wording. Premium route wording is for route transport such as rail,
    # flights, coaches and cruises.
    if row_type == "Transfer":
        return get_premium_transport_phrase(row) if is_route_transfer(row) else ""
    if row_type in TRANSPORT_TYPES:
        return get_premium_transport_phrase(row)
    return ""

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
    raw_name = row.get("hotel_name") or row.get("title") or "Accommodation"
    name = polish_hotel_name(re.sub(r"^Accommodation\s*:\s*Check[- ]?in\s+at\s+", "", str(raw_name), flags=re.IGNORECASE))
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
    title = clean_client_title(title, row) or title
    if "norway in a nutshell" in str(title).lower():
        return polish_title(title)
    return normalize_client_day_title(title, row)


def _clean_transport_title(row: dict) -> str:
    row_type = get_row_type(row)
    title = _clean(row.get("title", ""))
    details = _clean(row.get("details", ""))
    combined = f"{title} {details}".lower()

    if row_type == "Transfer":
        if is_route_transfer(row):
            return get_transfer_travel_title(row)
        # Parser standardization already knows the direction (hotel → airport,
        # airport → hotel, station → hotel, etc.). Reusing it prevents final
        # inclusions from flipping departure transfers into arrival transfers.
        clean_title = polish_title(title or "Private transfer")
        city = canonicalize_place_name(row.get("city", ""))
        if city and clean_title.lower() in {"private transfer to your accommodation", "private transfer from your accommodation"}:
            return f"{clean_title} in {city}"
        return clean_title

    if row_type in TRANSPORT_TYPES:
        return polish_title(title or get_transfer_travel_title(row))

    return polish_title(title)


def _transport_bucket(row: dict) -> str:
    text = f'{row.get("title", "")} {row.get("details", "")}'.lower()
    row_type = get_row_type(row)
    if "private" in text:
        return "Private transfers"
    if "self-guided" in text or "self transfer" in text:
        return ""
    if "norway in a nutshell" in text or "nærøyfjord" in text or "naeroyfjord" in text or "flåm" in text or "flam" in text:
        return "Scenic rail & fjord journeys"
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
    if _is_cruise_leisure_row(row):
        return ""
    title = get_premium_transport_phrase(row) or _route_transport_line(row) or _clean_transport_title(row)
    extras = []
    for item in row.get("includes", []) or []:
        item = sanitize_inclusion_item(item, title)
        if not item:
            continue
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
    cabin_match = re.search(r"\b(?:\d+\s*x\s*)?Cabin\s*\(([^)]+)\)", f'{row.get("details", "")} {row.get("original_title", "")}', flags=re.IGNORECASE)
    if get_row_type(row) == "Cruise" and cabin_match:
        _add_unique(extras, f"{polish_title(cabin_match.group(1))} cabin")
    luggage = polish_inclusion_item(row.get("luggage_included", ""), title)
    if luggage:
        _add_unique(extras, luggage)
    if extras:
        extras = merge_compound_inclusions(extras)
        detail = _join_detail_parts(extras).strip(" .")
        if detail:
            detail = re.sub(r"\bFull pension Meal plan\b", "full pension meal plan", detail, flags=re.IGNORECASE)
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


def _extract_rental_summary(rows: list[dict]) -> list[str]:
    source_rows = [row for row in rows if get_row_type(row) == "Day Overview" and re.search(r"rental\s+(?:vehicle|car|suv)|pick\s*up\s+rental|pickup\s+rental|drop\s+vehicle|return\s+vehicle", f'{row.get("title", "")} {row.get("details", "")}', flags=re.IGNORECASE)]
    examples: list[str] = []
    included: list[str] = []
    has_suv = False
    has_pickup = False
    has_drop = False
    for row in source_rows:
        text = f'{row.get("title", "")}\n{row.get("details", "")}'.replace("|", "\n").replace("✅", "")
        mode = "pickup"
        for raw in text.splitlines():
            line = _clean(raw).strip(" •-*:")
            if not line:
                continue
            lower = line.lower()
            if "rental suv" in lower or "suv" in lower:
                has_suv = True
            if "pick" in lower and "rental" in lower:
                has_pickup = True
            if "drop vehicle" in lower or "return vehicle" in lower:
                has_drop = True
            if lower in {"included", "includes"}:
                mode = "included"
                continue
            if lower.startswith("not included"):
                mode = "not_included"
                continue
            if "option" in lower and "similar category" in lower:
                mode = "examples"
                continue
            if mode == "examples" and not re.search(r"option|similar", lower):
                _add_unique(examples, polish_title(line))
            elif mode == "included":
                if lower == "automatic":
                    line = "Automatic transmission"
                _add_unique(included, polish_inclusion_item(line, "Rental vehicle"))
    items: list[str] = []
    vehicle_label = "Rental SUV" if has_suv else "Rental vehicle"
    if has_pickup:
        if examples:
            _add_unique(items, f"{vehicle_label}, such as a {examples[0]} or similar")
        else:
            _add_unique(items, f"{vehicle_label} or similar")
    if included:
        detail = _join_detail_parts([item.lower() if item != "GPS" else item for item in included]).strip(" .")
        if detail:
            _add_unique(items, detail[:1].upper() + detail[1:] + " included")
    if has_drop:
        _add_unique(items, "Rental vehicle return at the rental office or airport")
    return items


def _has_non_breakfast_meal(meal: str) -> bool:
    lower = _clean(meal).lower()
    return bool(lower and "breakfast" not in lower and "without" not in lower) or any(marker in lower for marker in ["dinner", "lunch", "full board", "half board", "full pension"])


def create_categorized_inclusions(parsed_rows, grouped_days=None) -> list[dict]:
    """Return inclusion sections as [{title, items}]."""

    rows = main_rows_only(parsed_rows)
    sections: list[dict] = []

    hotel_items: list[str] = []
    activity_items: list[str] = []
    transport_buckets: OrderedDict[str, list[str]] = OrderedDict()
    meal_items: list[str] = []

    if grouped_days:
        # Accommodation must read in itinerary order. Pull rows from the grouped
        # day structure because it contains synthetic group-tour overnights, and
        # because parsed_rows alone would put those placeholders after the real
        # post-tour hotel rows. Same-destination stays remain separate when they
        # occur at different points in the route.
        hotel_rows = []
        seen_hotel_keys = set()
        for day, day_rows in grouped_days.items():
            for row_index, row in enumerate(day_rows):
                if get_row_type(row) != "Hotel":
                    continue
                key = (
                    str(row.get("day", day)),
                    str(row.get("row_id", "")) or str(row_index),
                    _clean(row.get("hotel_name") or row.get("title")).lower(),
                    _clean(row.get("city", "")).lower(),
                )
                if key in seen_hotel_keys:
                    continue
                hotel_rows.append(row)
                seen_hotel_keys.add(key)
    else:
        hotel_rows = [row for row in rows if get_row_type(row) == "Hotel"]
    activity_rows = [row for row in rows if get_row_type(row) == "Activity"]

    for row in hotel_rows:
        _add_unique(hotel_items, _hotel_line(row))
        meal = _format_meal_plan(row.get("meal_plan", ""))
        city = canonicalize_place_name(row.get("city", ""))
        name = polish_hotel_name(row.get("hotel_name") or row.get("title") or "accommodation")
        # Breakfast already appears inside the Accommodation section. Only
        # keep a separate meals section for non-breakfast / board meals.
        if meal and _has_non_breakfast_meal(meal):
            _add_unique(meal_items, f"{meal.capitalize()} at {name}{', ' + city if city else ''}")

    for row in activity_rows:
        _add_unique(activity_items, _activity_line(row))

    for row in rows:
        row_type = get_row_type(row)
        if row_type not in set(TRANSPORT_TYPES) | {"Transfer"}:
            continue
        text_for_skip = f'{row.get("title", "")} {row.get("details", "")}'.lower()
        if is_self_arranged(row) or _is_self_transfer_row(row) or _is_cruise_leisure_row(row) or _is_cruise_arrival_row(row):
            continue
        if row_type == "Transfer" and text_for_skip.strip().startswith("arrival in") and "private" not in text_for_skip and "shuttle" not in text_for_skip:
            continue
        line = _transport_line(row)
        if not line:
            continue
        bucket = _transport_bucket(row)
        if not bucket:
            continue
        transport_buckets.setdefault(bucket, [])
        _add_unique(transport_buckets[bucket], line)

    if hotel_items:
        sections.append({"title": "Accommodation", "items": hotel_items})
    if activity_items:
        sections.append({"title": "Activities & experiences", "items": activity_items})
    rental_items = _extract_rental_summary(rows) if has_self_drive_markers(rows) else []
    if rental_items:
        sections.append({"title": "Rental vehicle", "items": rental_items})
    for bucket, items in transport_buckets.items():
        if items:
            sections.append({"title": bucket, "items": items})
    if meal_items:
        sections.append({"title": "Meals included", "items": meal_items})

    # Guide/local-support details are already shown within each relevant day.
    # Keeping them off the commercial inclusions summary avoids repetition and
    # prevents self-guided experiences from being misrepresented as guided.
    return sections

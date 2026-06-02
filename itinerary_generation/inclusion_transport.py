"""Transport inclusion summary helpers."""

import re

from place_aliases import canonicalize_place_name
from text_polish import polish_inclusion_item, polish_title

from itinerary_generation.common import TRANSPORT_TYPES, get_row_type
from itinerary_generation.content_engine import merge_compound_inclusions, sanitize_inclusion_item
from itinerary_generation.transport import get_transport_route_phrase, get_transfer_travel_title, is_route_transfer
from itinerary_generation.transport_model import TRANSPORT_CORE_FIELDS, get_transport_source_text
from itinerary_generation.transport_details import get_transport_detail_items
from itinerary_generation.transport_times import get_transport_time_text
from .inclusion_utils import add_unique, clean, join_detail_parts


def is_self_transfer_row(row: dict) -> bool:
    text = get_transport_source_text(row, TRANSPORT_CORE_FIELDS).lower()
    return get_row_type(row) == "Transfer" and "self transfer" in text


def is_cruise_leisure_row(row: dict) -> bool:
    text = get_transport_source_text(row, TRANSPORT_CORE_FIELDS).lower()
    return get_row_type(row) == "Cruise" and "leisure" in text and "cruise" in text


def is_cruise_arrival_row(row: dict) -> bool:
    text = get_transport_source_text(row, TRANSPORT_CORE_FIELDS).lower()
    return get_row_type(row) == "Cruise" and "arrival" in text


def route_transport_line(row: dict) -> str:
    row_type = get_row_type(row)
    # Private/self/local transfers should keep their standardized transfer
    # wording. Route wording is for route transport such as rail,
    # flights, coaches and cruises.
    if row_type == "Transfer":
        return get_transport_route_phrase(row) if is_route_transfer(row) else ""
    if row_type in TRANSPORT_TYPES:
        return get_transport_route_phrase(row)
    return ""


def clean_transport_title(row: dict) -> str:
    row_type = get_row_type(row)
    title = clean(row.get("title", ""))
    details = clean(row.get("details", ""))
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


def transport_bucket(row: dict) -> str:
    text = get_transport_source_text(row, TRANSPORT_CORE_FIELDS).lower()
    row_type = get_row_type(row)
    if "private" in text and get_row_type(row) == "Transfer" and not is_route_transfer(row):
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


def transport_line(row: dict) -> str:
    if is_cruise_leisure_row(row):
        return ""
    title = get_transport_route_phrase(row) or route_transport_line(row) or clean_transport_title(row)
    extras = []
    schedule = get_transport_time_text(row)
    if schedule and transport_bucket(row) not in {"Private transfers"}:
        add_unique(extras, schedule)
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
            add_unique(extras, item)
    cabin_match = re.search(r"\b(?:\d+\s*x\s*)?Cabin\s*\(([^)]+)\)", f'{row.get("title", "")} {row.get("details", "")} {row.get("original_title", "")}', flags=re.IGNORECASE)
    if get_row_type(row) == "Cruise" and cabin_match:
        add_unique(extras, f"{polish_title(cabin_match.group(1))} cabin")
    for detail_item in get_transport_detail_items(row, title):
        detail_item = polish_inclusion_item(detail_item, title)
        if detail_item:
            add_unique(extras, detail_item)
    if extras:
        schedule_lines = [item for item in extras if schedule and item == schedule]
        extras = [item for item in extras if not (schedule and item == schedule)]
        if any("car ticket" in item.lower() for item in extras):
            extras = [item for item in extras if item.lower() not in {"ticket included", "tickets included", "ferry ticket included"}]
        if any("coach ticket" in item.lower() for item in extras):
            extras = [item for item in extras if item.lower() not in {"ticket included", "tickets included"}]
        if any("train ticket" in item.lower() for item in extras):
            extras = [item for item in extras if item.lower() not in {"ticket included", "tickets included"}]
        extras = [item for item in extras if item]
        extras = [item for item in extras if "ticket included" not in item.lower()] + [item for item in extras if "ticket included" in item.lower()]
        extras = merge_compound_inclusions(extras)
        detail_lines = list(schedule_lines)
        detail = join_detail_parts(extras).strip(" .")
        if detail:
            detail = re.sub(r"\bFull pension Meal plan\b", "full pension meal plan", detail, flags=re.IGNORECASE)
            detail = detail[:1].upper() + detail[1:]
            detail_lines.append(f"{detail}.")
        if detail_lines:
            return f"{title}\n" + "\n".join(detail_lines)
    return title

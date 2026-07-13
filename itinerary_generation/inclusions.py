"""Canonical transport inclusion summary helpers."""

import re

from place_aliases import canonicalize_place_name
from text_polish import polish_inclusion_item, polish_title

from itinerary_generation.common import TRANSPORT_TYPES, get_row_type
from shared.commercial_markers import has_self_transfer_marker
from itinerary_generation.content_engine import merge_compound_inclusions, sanitize_inclusion_item
from itinerary_generation.transport_detection import is_route_transfer
from itinerary_generation.transport_domain.titles import get_transport_route_phrase, get_transfer_travel_title
from itinerary_generation.transport_model import TRANSPORT_CORE_FIELDS, get_transport_source_text
from itinerary_generation.transport_details import format_flight_luggage_detail, get_transport_detail_items
from itinerary_generation.transport_times import get_transport_time_text
from itinerary_generation.nutshell_domain import resolve_nutshell_journey
from itinerary_generation.transport_norway import format_norway_nutshell_route
from itinerary_generation.date_formatting import format_client_date
from itinerary_generation.inclusion_utils import add_unique, clean, join_detail_parts


def is_self_transfer_row(row: dict) -> bool:
    text = get_transport_source_text(row, TRANSPORT_CORE_FIELDS).lower()
    return get_row_type(row) == "Transfer" and has_self_transfer_marker(text)


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
    if "private" in text and row_type in {"Transfer", "Arrival", "Departure"} and not is_route_transfer(row):
        return "Private transfers"
    if "self-guided" in text or has_self_transfer_marker(text):
        return ""
    if resolve_nutshell_journey(row) is not None:
        return "Scenic rail & fjord journeys"
    if "nærøyfjord" in text or "naeroyfjord" in text or "flåm" in text or "flam" in text:
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


def _santa_claus_express_inclusion_line(row: dict, title: str) -> str:
    text = get_transport_source_text(row)
    if "santa claus express" not in text.lower():
        return ""
    lines = [title]
    schedule = get_transport_time_text(row)
    if schedule:
        lines.append(schedule)
    for detail_item in get_transport_detail_items(row, title):
        detail_item = polish_inclusion_item(detail_item, title)
        if not detail_item:
            continue
        if re.search(r"\bcabin\b", detail_item, flags=re.IGNORECASE) and not detail_item.lower().startswith("cabin"):
            detail_item = f"Cabin: {detail_item}"
        if detail_item.lower().startswith("cabin:") and not detail_item.endswith("."):
            detail_item = f"{detail_item}."
        if detail_item not in lines:
            lines.append(detail_item)
    return "\n".join(lines)


def _nutshell_inclusion_leg_line(leg) -> str:
    if not leg.origin or not leg.destination:
        return ""
    departure = str(leg.departure_time or "").strip()
    arrival = str(leg.arrival_time or "").strip()
    if departure and arrival:
        line = f"{departure} {leg.origin} - {arrival} {leg.destination}"
    elif departure:
        line = f"{departure} {leg.origin} - {leg.destination}"
    elif arrival:
        line = f"{leg.origin} - {arrival} {leg.destination}"
    else:
        line = f"{leg.origin} to {leg.destination}"
    return f"{line} — {leg.mode}" if leg.mode else line


def _norway_nutshell_inclusion_line(row: dict, title: str) -> str:
    journey = resolve_nutshell_journey(row)
    if journey is None:
        return ""

    lines = [journey.client_title]
    schedule = journey.journey_time or get_transport_time_text(row)
    if schedule:
        lines.append(schedule)

    timed_legs = [leg for leg in journey.legs if leg.departure_time or leg.arrival_time]
    if timed_legs and not journey.warnings:
        lines.append("Route details:")
        lines.extend(line for line in (_nutshell_inclusion_leg_line(leg) for leg in timed_legs) if line)
    elif len(journey.route_points) >= 3 and not journey.warnings:
        route_text = format_norway_nutshell_route(list(journey.route_points))
        if route_text:
            lines.append(f"Route highlights: {route_text}")

    source_items = journey.supplier_includes or journey.included_services
    includes = merge_compound_inclusions([
        polish_inclusion_item(sanitize_inclusion_item(item, journey.client_title), journey.client_title)
        for item in source_items
        if sanitize_inclusion_item(item, journey.client_title)
    ])
    if includes:
        detail = join_detail_parts(includes).strip(" .")
        if detail:
            lines.append(f"Included journey: {detail}.")
    return "\n".join(dict.fromkeys(line for line in lines if line))


def transport_line(row: dict) -> str:
    if is_cruise_leisure_row(row):
        return ""
    title = get_transport_route_phrase(row) or route_transport_line(row) or clean_transport_title(row)
    santa_line = _santa_claus_express_inclusion_line(row, title)
    if santa_line:
        return santa_line
    nutshell_line = _norway_nutshell_inclusion_line(row, title)
    if nutshell_line:
        return nutshell_line
    if transport_bucket(row) == "Private transfers":
        city = canonicalize_place_name(row.get("city", ""))
        date = format_client_date(row.get("start_date"))
        heading = " - ".join(part for part in [city, date] if part)
        clean_title = polish_title(title or "Private transfer").rstrip(" .")
        return f"{heading}\n{clean_title}." if heading else f"{clean_title}."
    extras = []
    schedule = get_transport_time_text(row)
    if schedule and transport_bucket(row) not in {"Private transfers"}:
        add_unique(extras, schedule)
    for item in row.get("includes", []) or []:
        if get_row_type(row) == "Flight" and format_flight_luggage_detail(item):
            continue
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
        extras = [re.sub(r"^Flight Tickets\b", "Flight tickets", item) for item in merge_compound_inclusions(extras)]
        provisional_notes = [
            item for item in extras
            if item.lower().startswith("train timing is provisional")
        ]
        extras = [item for item in extras if item not in provisional_notes]
        detail_lines = list(schedule_lines)
        detail = join_detail_parts(extras).strip(" .")
        if detail:
            detail = re.sub(r"\bFull pension Meal plan\b", "full pension meal plan", detail, flags=re.IGNORECASE)
            detail = detail[:1].upper() + detail[1:]
            detail_lines.append(f"{detail}.")
        for note in provisional_notes:
            clean_note = note.strip().rstrip(".")
            if clean_note:
                detail_lines.append(f"{clean_note}.")
        if detail_lines:
            return f"{title}\n" + "\n".join(detail_lines)
    return title

"""Structured client-facing transport detail extraction.

Transport rows arrive from supplier sheets as a mix of route, schedule and
commercial detail. These helpers extract reusable details once so day blocks,
final inclusions and legacy inclusion wrappers do not each invent their own
wording.
"""
from __future__ import annotations

import re

from text_polish import polish_title

from itinerary_generation.common import get_row_type
from itinerary_generation.train_details import get_train_cabin_detail
from itinerary_generation.transport_model import get_transport_source_text
from itinerary_generation.transport_times import get_overnight_train_schedule
from .inclusion_utils import add_unique, clean


_SEAT_CLASS_WORDS = r"(?:standard|premier|first|second|premium|business|economy|comfort|reserved|seat|seats|class|carriage|compartment|berth|upper|lower|downstairs|upstairs)"


def _strip_schedule_tail(value: str) -> str:
    text = clean(value).strip(" .,-:|")
    text = re.split(r"\s+-\s+(?:tickets?|ticket|luggage|meal|includes?|included|excludes?)\b", text, maxsplit=1, flags=re.IGNORECASE)[0]
    return clean(text).strip(" .,-:|")


def _normalize_quantity_detail(value: str) -> str:
    text = polish_title(clean(value)).strip(" .,-:|")
    text = re.sub(r"^(\d+)\s*[xX]\s+", r"\1 x ", text)
    text = re.sub(r"\bClass Seats\b", "class seats", text)
    text = re.sub(r"\bStandard Class\b", "standard class", text)
    text = re.sub(r"\bStandard Premier\b", "Standard Premier", text)
    text = re.sub(r"\bFirst Class\b", "first class", text)
    text = re.sub(r"\bSecond Class\b", "second class", text)
    text = re.sub(r"\bSeats\b", "seats", text)
    return text


def _extract_train_seat_detail(source: str) -> str:
    """Return explicit non-cabin train seat/class quantities."""

    text = str(source or "")
    if not text.strip() or not re.search(r"\btrain\b|\brail\b", text, flags=re.IGNORECASE):
        return ""
    if re.search(r"\bcabin\b", text, flags=re.IGNORECASE):
        return ""

    quantity_match = re.search(
        rf"\b(\d+\s*x\s*(?:{_SEAT_CLASS_WORDS}\s+){{0,5}}(?:seats?|tickets?|berths?))\b",
        text,
        flags=re.IGNORECASE,
    )
    if quantity_match:
        detail = _normalize_quantity_detail(_strip_schedule_tail(quantity_match.group(1)))
        if re.search(r"\btickets?\b", detail, flags=re.IGNORECASE):
            return ""
        return detail

    class_match = re.search(
        r"\b((?:standard|premier|first|second|premium|business|economy|comfort)(?:\s+(?:premier|class))*\s+(?:seats?|tickets?))\b",
        text,
        flags=re.IGNORECASE,
    )
    if class_match:
        detail = _normalize_quantity_detail(class_match.group(1))
        if "ticket" not in detail.lower():
            return detail
    return ""


def _extract_ticket_detail(source: str, row_type: str, title: str) -> str:
    text = str(source or "")
    lower = text.lower()
    context = f"{row_type} {title}".lower()

    if re.search(r"\bcar\s+ticket\s+included\b", lower):
        return "car ticket included"
    if re.search(r"\bcoach\s+ticket\s+included\b|\bbus\s+ticket\s+included\b", lower):
        return "coach ticket included"
    if re.search(r"\btrain\s+ticket\s+included\b", lower):
        return "train ticket included"
    if re.search(r"\b(?:dinner|breakfast|lunch|meal)\s+included\b", lower):
        meal = re.search(r"\b(dinner|breakfast|lunch|meal)\s+included\b", lower)
        if meal:
            return f"{meal.group(1)} included"
    if re.search(r"\btickets?\s+included\b", lower):
        if "coach" in context or "bus" in context:
            return "coach ticket included"
        if "train" in context:
            return "train ticket included"
        if "ferry" in context:
            return "ferry ticket included"
        if "cruise" in context:
            return "cruise ticket included"
        return "ticket included"
    return ""


def format_flight_luggage_detail(source: str) -> str:
    """Return client-ready flight ticket and baggage wording when detected."""

    text = str(source or "")
    checked = re.search(r"(\d+)\s*x\s*(\d+)\s*kg\s*(?:check(?:ed)?[ -]?in|checked)\s*(?:bag|baggage|luggage)?", text, flags=re.IGNORECASE)
    carry = re.search(r"(\d+)\s*x\s*(\d+)\s*kg\s*carry[- ]?on\s*(?:bag|baggage|luggage)?", text, flags=re.IGNORECASE)
    if checked or carry:
        parts = ["Flight tickets"]
        if checked:
            parts.append(f"{checked.group(1)} x {checked.group(2)} kg checked bag")
        if carry:
            parts.append(f"{carry.group(1)} x {carry.group(2)} kg carry-on bag")
        return ", ".join(parts) + " per person"
    match = re.search(r"\b((?:\d+\s*x?\s*)?)(checked\s+bag|checked\s+baggage|checked\s+luggage|cabin\s+bag|carry[-\s]?on\s+bag|luggage)\s+included\b", text, flags=re.IGNORECASE)
    if not match:
        return ""
    prefix = (match.group(1) or "").strip()
    item = match.group(2).lower().replace("baggage", "luggage")
    item = re.sub(r"^checked\s+bag$", "checked luggage", item)
    return f"{prefix} {item} included".strip()


def _extract_luggage_detail(source: str) -> str:
    return format_flight_luggage_detail(source)


def _extract_cruise_cabin_detail(source: str) -> str:
    text = str(source or "")
    if not re.search(r"\b(?:cruise|ferry)\b", text, flags=re.IGNORECASE):
        return ""
    paren_match = re.search(r"\b(?:\d+\s*x\s*)?Cabin\s*\(([^)]+)\)", text, flags=re.IGNORECASE)
    if paren_match:
        return f"{polish_title(paren_match.group(1))} cabin"
    quantity_match = re.search(
        r"\b(\d+\s*x\s*(?:(?:inside|outside|sea\s*view|seaview|ocean\s*view|standard|premium|superior|deluxe|double|single|twin|family)\s+){0,4}cabin(?:s)?)\b",
        text,
        flags=re.IGNORECASE,
    )
    if quantity_match:
        return _normalize_quantity_detail(quantity_match.group(1))
    descriptive_match = re.search(
        r"\b((?:(?:inside|outside|sea\s*view|seaview|ocean\s*view|standard|premium|superior|deluxe|double|single|twin|family)\s+){1,4}cabin(?:s)?)\b",
        text,
        flags=re.IGNORECASE,
    )
    if descriptive_match:
        return _normalize_quantity_detail(descriptive_match.group(1))
    return ""


def _extract_train_service(source: str) -> str:
    """Return a named train service/number without reinterpreting its route."""

    text = str(source or "")
    match = re.search(r"\bInterCity\s*(\d+)\b", text, flags=re.IGNORECASE)
    if match:
        return f"InterCity {match.group(1)}"
    match = re.search(r"\bIC\s*(\d+)\b", text, flags=re.IGNORECASE)
    if match:
        return f"IC {match.group(1)}"
    return ""


def _extract_provisional_train_note(source: str) -> str:
    """Preserve supplier caveats that make a displayed train time provisional."""

    text = str(source or "")
    if not re.search(r"\b(?:train|intercity|rail)\b", text, flags=re.IGNORECASE):
        return ""
    if re.search(
        r"dates?\s+not\s+yet\s+released|tim(?:e|ing)s?\s+to\s+be\s+confirmed|confirm(?:ed|ation).*?final\s+voucher|final\s+(?:travel\s+)?voucher",
        text,
        flags=re.IGNORECASE,
    ):
        return "Train timing is provisional and will be confirmed in the final travel voucher"
    return ""


def get_transport_detail_items(row: dict, title: str = "") -> list[str]:
    """Return deduplicated details suitable below a transport route title."""

    row_type = get_row_type(row)
    source = get_transport_source_text(row)
    title = title or str(row.get("title", "") or "")
    details: list[str] = []

    train_service = _extract_train_service(source)
    if train_service:
        add_unique(details, train_service)

    schedule = get_overnight_train_schedule(row)
    if schedule.get("departure_time") and schedule.get("departure_place"):
        add_unique(details, f'Departure: {schedule["departure_time"]} from {polish_title(schedule["departure_place"])}')
    if schedule.get("arrival_time") and schedule.get("arrival_place"):
        add_unique(details, f'Arrival: {schedule["arrival_time"]} in {polish_title(schedule["arrival_place"])}')

    train_cabin = get_train_cabin_detail(row)
    if train_cabin:
        add_unique(details, train_cabin)
    else:
        seat_detail = _extract_train_seat_detail(source)
        if seat_detail:
            add_unique(details, seat_detail)

    cruise_cabin = _extract_cruise_cabin_detail(source)
    if cruise_cabin:
        add_unique(details, cruise_cabin)

    ticket_detail = _extract_ticket_detail(source, row_type, title)
    if ticket_detail:
        add_unique(details, ticket_detail)

    luggage_source = clean(row.get("luggage_included", ""))
    luggage = format_flight_luggage_detail(luggage_source or source)
    if not luggage and luggage_source:
        luggage = luggage_source
    if not luggage:
        luggage = _extract_luggage_detail(source)
    if luggage:
        add_unique(details, luggage)

    provisional_note = _extract_provisional_train_note(source)
    if provisional_note:
        add_unique(details, provisional_note)

    return details

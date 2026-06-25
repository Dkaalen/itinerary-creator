"""Row classification and title helpers for itinerary exclusions."""

from __future__ import annotations

from itinerary_generation.client_sanitizer import sanitize_client_text
from itinerary_generation.common import get_row_type
from itinerary_generation.date_formatting import format_client_date
from itinerary_generation.titles import create_client_activity_title
from itinerary_generation.transport_domain.exclusions import (
    is_flight_row as _transport_is_flight_row,
    is_self_transfer_row as _transport_is_self_transfer_row,
    is_transport_row as _transport_is_transport_row,
    row_search_text as _transport_row_search_text,
    self_arranged_flight_notice as _transport_self_arranged_flight_notice,
    self_transfer_exclusion_title as _transport_self_transfer_exclusion_title,
    transport_commercial_title as _transport_commercial_title,
)
from text_polish import polish_title


def _commercial_status(row):
    return str(row.get("commercial_status") or "").strip().lower()


def _commercial_reason(row):
    return str(row.get("commercial_reason") or "").strip().lower()


def _row_search_text(row):
    return _transport_row_search_text(row)


def _is_self_transfer_row(row):
    return _transport_is_self_transfer_row(row)


def _is_flight_row(row):
    return _transport_is_flight_row(row)


def _is_transport_row(row):
    return _transport_is_transport_row(row)


def _is_cost_not_included_row(row):
    text = _row_search_text(row)
    return (
        _commercial_reason(row) == "cost_not_included"
        or "cost not included" in text
        or "price not included" in text
        or "not included" in text
        or "without meal" in text
        or "to be bought on site" in text
        or "to be bought on spot" in text
        or "ticket counter" in text
        or "on spot" in text
        or "on site" in text
    )


def _rental_cost_not_included_label(row):
    """Return a precise rental cost exclusion without excluding the rental row."""

    text = _row_search_text(row)
    if "rental" not in text or "not included" not in text:
        return ""
    if "deposit" in text:
        return "Rental vehicle safety deposit"
    if "fuel" in text:
        return "Rental vehicle fuel costs"
    if "parking" in text:
        return "Rental vehicle parking costs"
    return "Rental vehicle costs marked as not included"


def row_date_suffix(row):
    text = format_client_date(row.get("start_date"))
    return f" - {text}" if text else ""


def self_arranged_flight_notice(row) -> str:
    """Return a clear commercial exclusion label for a self-arranged flight."""

    return _transport_self_arranged_flight_notice(row)


def commercial_row_title(row):
    row_type = get_row_type(row)
    title = ""
    if _is_self_transfer_row(row):
        return _transport_self_transfer_exclusion_title(row)
    if row_type == "Activity":
        title = create_client_activity_title(row)
    if not title:
        title = _transport_commercial_title(row)
    title = title or row.get("title") or row.get("original_title") or row.get("details")
    title = sanitize_client_text(polish_title(str(title or "").strip()))
    return title[:120].strip(" -:|")

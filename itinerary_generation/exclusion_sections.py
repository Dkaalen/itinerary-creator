"""Structured "what's not included" list helpers.

Exclusions are generated from commercial row status rather than from preview or
PDF presentation code. Keeping this isolated makes optional/self-arranged rules
less likely to leak into inclusion rendering.
"""

from text_polish import polish_title

from itinerary_generation.common import (
    TRANSPORT_TYPES,
    add_unique,
    get_row_type,
    main_rows_only,
    optional_rows_only,
    is_self_arranged,
)
from itinerary_generation.transport import (
    get_transfer_travel_title,
    get_transport_route_phrase,
)
from itinerary_generation.date_formatting import format_client_date
from itinerary_generation.titles import create_client_activity_title


DEFAULT_WHATS_NOT_INCLUDED_ITEMS = [
    "International flights unless specifically listed",
    "Meals unless specifically stated",
    "Drinks unless specifically stated",
    "Porterage unless specified",
    "Self transfers and self-arranged travel costs unless specifically stated",
    "Travel insurance",
    "Optional extras and personal expenses",
    "City taxes or local fees, where applicable",
]


def row_date_suffix(row):
    text = format_client_date(row.get("start_date"))
    return f" - {text}" if text else ""


def commercial_row_title(row):
    row_type = get_row_type(row)
    title = ""
    if row_type == "Activity":
        title = create_client_activity_title(row)
    if not title and row_type in set(TRANSPORT_TYPES) | {"Transfer"}:
        title = get_transport_route_phrase(row) or get_transfer_travel_title(row)
    title = title or row.get("title") or row.get("original_title") or row.get("details")
    title = polish_title(str(title or "").strip())
    return title[:120].strip(" -:|")


def specific_self_arranged_items(parsed_rows):
    items = []
    for row in main_rows_only(parsed_rows or []):
        text = f'{row.get("title", "")} {row.get("details", "")}'.lower()
        if not (is_self_arranged(row) or row.get("commercial_status") == "self_arranged" or "self transfer" in text):
            continue
        title = commercial_row_title(row)
        if not title:
            continue
        label = f"{title}{row_date_suffix(row)}"
        add_unique(items, label)
    return items


def specific_optional_items(parsed_rows):
    items = []
    for row in optional_rows_only(parsed_rows or []):
        title = commercial_row_title(row)
        if not title:
            continue
        add_unique(items, f"{title}{row_date_suffix(row)}")
    return items


def create_whats_not_included(parsed_rows=None):
    rows = parsed_rows or []
    items = list(DEFAULT_WHATS_NOT_INCLUDED_ITEMS)
    text = " ".join(f'{row.get("title", "")} {row.get("details", "")}' for row in rows).lower()

    self_arranged_items = specific_self_arranged_items(rows)
    if self_arranged_items:
        note = "Self-arranged flights or transport listed in the itinerary, unless specifically stated as included: " + "; ".join(self_arranged_items[:8])
        if len(self_arranged_items) > 8:
            note += f"; and {len(self_arranged_items) - 8} more"
        if note not in items:
            items.insert(1, note)

    optional_items = specific_optional_items(rows)
    if optional_items:
        note = "Optional experiences unless specifically confirmed: " + "; ".join(optional_items[:8])
        if len(optional_items) > 8:
            note += f"; and {len(optional_items) - 8} more"
        if note not in items:
            items.insert(1, note)
        legacy_note = "Optional add-ons and experiences unless specifically selected"
        if legacy_note not in items:
            items.insert(1, legacy_note)

    if "optional addon" in text or "optional add-on" in text or "optional add on" in text:
        note = "Optional add-ons and experiences unless specifically selected"
        if note not in items:
            items.insert(1, note)
    if "excludes" in text or "not included" in text or "to be bought on site" in text:
        note = "Tickets or services marked as excluded or to be bought on site"
        if note not in items:
            items.insert(1, note)
    return items

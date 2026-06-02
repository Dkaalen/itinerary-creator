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
    is_optional_row,
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
    "Optional experiences unless specifically confirmed",
    "City taxes or local fees, where applicable",
]


EXCLUSION_SECTION_ORDER = [
    ("self_arranged_flights", "Self-arranged flights"),
    ("self_transfers", "Self transfers"),
    ("optional_experiences", "Optional experiences"),
    ("optional_transfers", "Optional transfers"),
    ("optional_hotels", "Optional hotels/add-ons"),
    ("costs_not_included", "Costs not included"),
]


TRANSPORT_ROW_TYPES = set(TRANSPORT_TYPES) | {"Transfer", "Transport", "Train", "Flight", "Cruise", "Ferry", "Drive"}


def _commercial_status(row):
    return str(row.get("commercial_status") or "").strip().lower()


def _commercial_reason(row):
    return str(row.get("commercial_reason") or "").strip().lower()


def _row_search_text(row):
    return " ".join(
        str(row.get(key, "") or "")
        for key in ["source_type", "type", "effective_type", "title", "original_title", "details"]
    ).lower().replace("-", " ")


def _is_self_transfer_row(row):
    return "self transfer" in _row_search_text(row)


def _is_flight_row(row):
    return get_row_type(row) == "Flight" or "flight" in _row_search_text(row)


def _is_transport_row(row):
    text = _row_search_text(row)
    return get_row_type(row) in TRANSPORT_ROW_TYPES or any(
        marker in text
        for marker in ["transfer", "flight", "train", "coach", "bus", "ferry", "cruise", "shuttle"]
    )


def _is_cost_not_included_row(row):
    text = _row_search_text(row)
    return (
        _commercial_reason(row) == "cost_not_included"
        or "cost not included" in text
        or "price not included" in text
        or "not included" in text
        or "to be bought on site" in text
    )


def _rental_cost_not_included_label(row):
    """Return a precise rental cost exclusion without excluding the rental row.

    Supplier rows commonly describe the included rental package and then add a
    small commercial caveat such as ``Not included: Safety deposit``. The final
    exclusions should surface the caveat, not the whole rental pick-up title.
    """

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


def create_specific_exclusion_sections(parsed_rows):
    """Return itinerary-specific exclusions grouped under client-facing headings.

    The grouping is intentionally driven by row commercial metadata first and
    conservative text markers second. That keeps optional/self-arranged logic
    from becoming a broad text search that can accidentally affect later rows.
    """

    sections = {key: [] for key, _ in EXCLUSION_SECTION_ORDER}

    for row in parsed_rows or []:
        title = commercial_row_title(row)
        if not title:
            continue

        label = f"{title}{row_date_suffix(row)}"
        row_type = get_row_type(row)
        status = _commercial_status(row)

        rental_exclusion = _rental_cost_not_included_label(row)
        if rental_exclusion:
            add_unique(sections["costs_not_included"], rental_exclusion)
            # The included rental row can continue through normal inclusion
            # handling, but it should not add a raw pick-up title to exclusions.
            continue

        if is_optional_row(row):
            if row_type == "Activity":
                add_unique(sections["optional_experiences"], label)
            elif row_type == "Hotel":
                add_unique(sections["optional_hotels"], label)
            elif _is_transport_row(row):
                add_unique(sections["optional_transfers"], label)
            else:
                add_unique(sections["optional_hotels"], label)
            continue

        if status == "self_arranged" or is_self_arranged(row) or _is_self_transfer_row(row):
            if _is_self_transfer_row(row):
                add_unique(sections["self_transfers"], label)
            elif _is_flight_row(row):
                add_unique(sections["self_arranged_flights"], label)
            else:
                add_unique(sections["costs_not_included"], label)
            continue

        if status == "excluded" or _is_cost_not_included_row(row):
            add_unique(sections["costs_not_included"], label)

    return {key: value for key, value in sections.items() if value}


def flatten_specific_exclusion_sections(sections, limit_per_section=8):
    """Flatten structured exclusion sections for the existing final-page renderer."""

    items = []
    for key, heading in EXCLUSION_SECTION_ORDER:
        section_items = list((sections or {}).get(key) or [])
        if not section_items:
            continue
        add_unique(items, heading)
        for item in section_items[:limit_per_section]:
            add_unique(items, item)
        if len(section_items) > limit_per_section:
            add_unique(items, f"and {len(section_items) - limit_per_section} more")
    return items


def create_whats_not_included(parsed_rows=None):
    rows = parsed_rows or []
    items = list(DEFAULT_WHATS_NOT_INCLUDED_ITEMS)
    text = " ".join(f'{row.get("title", "")} {row.get("details", "")}' for row in rows).lower()

    sections = create_specific_exclusion_sections(rows)
    structured_items = flatten_specific_exclusion_sections(sections)
    itinerary_specific_items = list(structured_items)

    if any(sections.get(key) for key in ["self_arranged_flights", "self_transfers", "costs_not_included"]):
        add_unique(itinerary_specific_items, "Self-arranged flights or transport unless specifically stated as included")

    if any(sections.get(key) for key in ["optional_experiences", "optional_transfers", "optional_hotels"]):
        add_unique(itinerary_specific_items, "Optional add-ons and experiences unless specifically selected")

    if "optional addon" in text or "optional add-on" in text or "optional add on" in text:
        add_unique(itinerary_specific_items, "Optional add-ons and experiences unless specifically selected")
    if "excludes" in text or "not included" in text or "to be bought on site" in text:
        add_unique(itinerary_specific_items, "Tickets or services marked as excluded or to be bought on site")

    if itinerary_specific_items:
        items = items[:1] + itinerary_specific_items + items[1:]
    return items

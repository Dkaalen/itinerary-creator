"""Build itinerary-specific exclusion sections from parsed rows."""

from __future__ import annotations

from itinerary_generation.client_sanitizer import sanitize_client_text
from itinerary_generation.common import add_unique, get_row_type, is_optional_row, is_self_arranged, main_rows_only, optional_rows_only
from itinerary_generation.exclusion_constants import EXCLUSION_SECTION_ORDER
from itinerary_generation.accommodation_display_helpers import (
    is_self_arranged_accommodation,
    self_arranged_accommodation_label,
)
from itinerary_generation.exclusion_row_rules import (
    _commercial_status,
    _is_cost_not_included_row,
    _is_flight_row,
    _is_self_transfer_row,
    _is_transport_row,
    _rental_cost_not_included_label,
    _row_search_text,
    commercial_row_title,
    row_date_suffix,
)
from itinerary_generation.exclusion_source_items import _specific_cost_not_included_label
from itinerary_generation.transport_safety import split_self_transfer_notes
from shared.source_rows import source_row_id


def _row_id(row, fallback_index=0):
    return source_row_id(row or {}, fallback_index)


def _structured_item(label, row=None, row_index=0):
    text = str(label or "").strip()
    if not text:
        return None
    source_ids = []
    if row is not None:
        row_id = _row_id(row, row_index)
        if row_id:
            source_ids.append(row_id)
    return {"label": text, "source_row_ids": source_ids}


def _self_arranged_accommodation_exclusion_label(row) -> str:
    return sanitize_client_text(f"{self_arranged_accommodation_label(row)}{row_date_suffix(row)}")


def specific_self_arranged_items(parsed_rows):
    items = []
    for row in main_rows_only(parsed_rows or []):
        text = f'{row.get("title", "")} {row.get("details", "")}'.lower()
        if not (is_self_arranged(row) or row.get("commercial_status") == "self_arranged" or "self transfer" in text):
            continue
        title = sanitize_client_text(commercial_row_title(row))
        if is_self_arranged_accommodation(row):
            title = self_arranged_accommodation_label(row)
        if not title:
            continue
        label = sanitize_client_text(f"{title}{row_date_suffix(row)}")
        add_unique(items, label)
    return items


def specific_optional_items(parsed_rows):
    items = []
    for row in optional_rows_only(parsed_rows or []):
        title = sanitize_client_text(commercial_row_title(row))
        if not title:
            continue
        add_unique(items, f"{title}{row_date_suffix(row)}")
    return items


def _section_key_for_row(row, row_type: str) -> str:
    if row_type == "Activity":
        return "optional_experiences"
    if row_type == "Hotel":
        return "optional_hotels"
    if _is_transport_row(row):
        return "optional_transfers"
    return "optional_hotels"


def create_specific_exclusion_sections(parsed_rows):
    """Return itinerary-specific exclusions grouped under client-facing headings."""

    sections = {key: [] for key, _ in EXCLUSION_SECTION_ORDER}
    for row in parsed_rows or []:
        title = sanitize_client_text(commercial_row_title(row))
        if not title:
            continue

        label = sanitize_client_text(f"{title}{row_date_suffix(row)}")
        row_type = str(row.get("group_tour_semantic_type") or get_row_type(row))
        status = _commercial_status(row)

        rental_exclusion = _rental_cost_not_included_label(row)
        if rental_exclusion:
            add_unique(sections["costs_not_included"], rental_exclusion)
            continue

        if is_optional_row(row):
            add_unique(sections[_section_key_for_row(row, row_type)], label)
            continue

        if status == "self_arranged" or is_self_arranged(row) or _is_self_transfer_row(row):
            if is_self_arranged_accommodation(row):
                add_unique(sections["self_arranged_accommodation"], _self_arranged_accommodation_exclusion_label(row))
            elif _is_self_transfer_row(row):
                add_unique(sections["self_transfers"], label)
                notes = split_self_transfer_notes(_row_search_text(row))
                if any("private transfer may" in note.lower() for note in notes):
                    add_unique(sections["costs_not_included"], "Private transfer supplement, if requested locally")
            elif _is_flight_row(row):
                add_unique(sections["self_arranged_flights"], label)
            else:
                add_unique(sections["costs_not_included"], label)
            continue

        if status == "excluded" or _is_cost_not_included_row(row):
            specific_label = _specific_cost_not_included_label(row)
            add_unique(sections["costs_not_included"], specific_label or label)

    return {key: value for key, value in sections.items() if value}


def _add_unique_structured(items, label, row=None, row_index=0):
    item = _structured_item(label, row=row, row_index=row_index)
    if not item:
        return
    key = (item["label"].lower(), tuple(item.get("source_row_ids") or ()))
    existing = {
        (str(current.get("label", "")).lower(), tuple(current.get("source_row_ids") or ()))
        for current in items
        if isinstance(current, dict)
    }
    if key not in existing:
        items.append(item)


def create_source_aware_exclusion_sections(parsed_rows):
    """Return itinerary-specific exclusions with source-row identity preserved."""

    sections = {key: [] for key, _ in EXCLUSION_SECTION_ORDER}
    for row_index, row in enumerate(parsed_rows or []):
        title = sanitize_client_text(commercial_row_title(row))
        if not title:
            continue

        label = sanitize_client_text(f"{title}{row_date_suffix(row)}")
        row_type = str(row.get("group_tour_semantic_type") or get_row_type(row))
        status = _commercial_status(row)

        rental_exclusion = _rental_cost_not_included_label(row)
        if rental_exclusion:
            _add_unique_structured(sections["costs_not_included"], rental_exclusion, row, row_index)
            continue

        if is_optional_row(row):
            _add_unique_structured(sections[_section_key_for_row(row, row_type)], label, row, row_index)
            continue

        if status == "self_arranged" or is_self_arranged(row) or _is_self_transfer_row(row):
            if is_self_arranged_accommodation(row):
                _add_unique_structured(sections["self_arranged_accommodation"], _self_arranged_accommodation_exclusion_label(row), row, row_index)
            elif _is_self_transfer_row(row):
                _add_unique_structured(sections["self_transfers"], label, row, row_index)
                notes = split_self_transfer_notes(_row_search_text(row))
                if any("private transfer may" in note.lower() for note in notes):
                    _add_unique_structured(sections["costs_not_included"], "Private transfer supplement, if requested locally", row, row_index)
            elif _is_flight_row(row):
                _add_unique_structured(sections["self_arranged_flights"], label, row, row_index)
            else:
                _add_unique_structured(sections["costs_not_included"], label, row, row_index)
            continue

        if status == "excluded" or _is_cost_not_included_row(row):
            specific_label = _specific_cost_not_included_label(row)
            _add_unique_structured(sections["costs_not_included"], specific_label or label, row, row_index)

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

"""Build final what's-not-included outputs."""

from __future__ import annotations

from itinerary_generation.common import add_unique, is_self_arranged
from itinerary_generation.exclusion_constants import DEFAULT_WHATS_NOT_INCLUDED_ITEMS, EXCLUSION_SECTION_ORDER
from itinerary_generation.exclusion_row_rules import _commercial_status, _is_flight_row, self_arranged_flight_notice
from itinerary_generation.exclusion_specific_sections import (
    _structured_item,
    create_source_aware_exclusion_sections,
    create_specific_exclusion_sections,
    flatten_specific_exclusion_sections,
)


def _commercial_rule_item(label, source_sections):
    source_ids = []
    for items in (source_sections or {}).values():
        for item in items or []:
            if not isinstance(item, dict):
                continue
            for row_id in item.get("source_row_ids") or []:
                if row_id and row_id not in source_ids:
                    source_ids.append(row_id)
    return {"label": label, "source_row_ids": source_ids[:20]}


def _default_exclusion_items():
    return [{"label": item, "source_row_ids": []} for item in DEFAULT_WHATS_NOT_INCLUDED_ITEMS]


def _rows_text(rows) -> str:
    return " ".join(f'{row.get("title", "")} {row.get("details", "")}' for row in rows).lower()


def create_structured_whats_not_included(parsed_rows=None):
    """Return exclusions as source-aware structured sections."""

    rows = parsed_rows or []
    text = _rows_text(rows)
    specific_sections = create_source_aware_exclusion_sections(rows)

    sections = []
    for key, heading in EXCLUSION_SECTION_ORDER:
        items = list(specific_sections.get(key) or [])
        if items:
            sections.append({"section_id": key, "title": heading, "items": items})

    commercial_rules = []
    if any(specific_sections.get(key) for key in ["self_arranged_flights", "self_transfers", "costs_not_included"]):
        commercial_rules.append(_commercial_rule_item(
            "Self-arranged flights or transport unless specifically stated as included",
            {key: specific_sections.get(key) or [] for key in ["self_arranged_flights", "self_transfers", "costs_not_included"]},
        ))
        for row_index, row in enumerate(rows):
            if (_commercial_status(row) == "self_arranged" or is_self_arranged(row)) and _is_flight_row(row):
                notice = _structured_item(self_arranged_flight_notice(row), row=row, row_index=row_index)
                if notice and notice["label"] not in {item.get("label") for item in commercial_rules if isinstance(item, dict)}:
                    commercial_rules.append(notice)
    if any(specific_sections.get(key) for key in ["optional_experiences", "optional_transfers", "optional_hotels"]):
        commercial_rules.append(_commercial_rule_item(
            "Optional add-ons and experiences unless specifically selected",
            {key: specific_sections.get(key) or [] for key in ["optional_experiences", "optional_transfers", "optional_hotels"]},
        ))
    if "optional addon" in text or "optional add-on" in text or "optional add on" in text:
        item = _commercial_rule_item("Optional add-ons and experiences unless specifically selected", specific_sections)
        if item["label"] not in {existing["label"] for existing in commercial_rules}:
            commercial_rules.append(item)
    if "excludes" in text or "not included" in text or "to be bought on site" in text or "to be bought on spot" in text or "ticket counter" in text:
        item = _commercial_rule_item("Tickets or services marked as excluded or to be bought on site", specific_sections)
        if item["label"] not in {existing["label"] for existing in commercial_rules}:
            commercial_rules.append(item)
    if commercial_rules:
        sections.append({"section_id": "commercial_rules", "title": "Commercial notes", "items": commercial_rules})

    sections.append({"section_id": "general", "title": "General exclusions", "items": _default_exclusion_items()})
    return sections


def create_whats_not_included(parsed_rows=None):
    rows = parsed_rows or []
    items = list(DEFAULT_WHATS_NOT_INCLUDED_ITEMS)
    text = _rows_text(rows)

    sections = create_specific_exclusion_sections(rows)
    itinerary_specific_items = list(flatten_specific_exclusion_sections(sections))

    if any(sections.get(key) for key in ["self_arranged_flights", "self_transfers", "costs_not_included"]):
        add_unique(itinerary_specific_items, "Self-arranged flights or transport unless specifically stated as included")

    if any(sections.get(key) for key in ["optional_experiences", "optional_transfers", "optional_hotels"]):
        add_unique(itinerary_specific_items, "Optional add-ons and experiences unless specifically selected")

    if "optional addon" in text or "optional add-on" in text or "optional add on" in text:
        add_unique(itinerary_specific_items, "Optional add-ons and experiences unless specifically selected")
    if "excludes" in text or "not included" in text or "to be bought on site" in text or "to be bought on spot" in text or "ticket counter" in text:
        add_unique(itinerary_specific_items, "Tickets or services marked as excluded or to be bought on site")

    if itinerary_specific_items:
        items = items[:1] + itinerary_specific_items + items[1:]
    return items

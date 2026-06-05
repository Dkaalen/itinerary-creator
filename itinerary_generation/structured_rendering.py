"""Adapters from structured itinerary model objects to renderer-friendly data.

Renderers should accept the strongly typed model directly where possible, but a
small adapter keeps the current dict/string renderers stable during the
migration.  This module is intentionally free of Streamlit, HTML and PDF
imports.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from itinerary_generation.structured_model import StructuredListItem, StructuredListSection


def _value(obj: Any, key: str, default: Any = "") -> Any:
    """Read either dataclass/object attributes or mapping keys."""

    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def normalize_structured_list_item(item: Any) -> StructuredListItem | None:
    """Return a clean StructuredListItem for strings, dicts or dataclasses."""

    if item is None:
        return None
    if isinstance(item, StructuredListItem):
        label = str(item.label or "").strip()
        details = tuple(str(line or "").strip() for line in item.detail_lines or () if str(line or "").strip())
        if not label and not details:
            return None
        return StructuredListItem(
            label=label or (details[0] if details else ""),
            detail_lines=details if label else details[1:],
            source_row_ids=tuple(str(row_id) for row_id in item.source_row_ids or () if str(row_id).strip()),
            category=str(item.category or "").strip(),
        )
    if is_dataclass(item):
        item = asdict(item)
    if isinstance(item, dict):
        label = str(item.get("label") or item.get("title") or item.get("text") or "").strip()
        raw_details = item.get("detail_lines") or item.get("details") or []
        if isinstance(raw_details, str):
            raw_details = [line for line in raw_details.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
        details = tuple(str(line or "").strip() for line in raw_details if str(line or "").strip())
        source_ids = item.get("source_row_ids") or item.get("source_ids") or ()
        if isinstance(source_ids, str):
            source_ids = (source_ids,)
        if not label and not details:
            return None
        return StructuredListItem(
            label=label or (details[0] if details else ""),
            detail_lines=details if label else details[1:],
            source_row_ids=tuple(str(row_id) for row_id in source_ids if str(row_id).strip()),
            category=str(item.get("category") or "").strip(),
        )

    lines = [line.strip() for line in str(item or "").replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip()]
    if not lines:
        return None
    return StructuredListItem(label=lines[0], detail_lines=tuple(lines[1:]))


def normalize_structured_list_section(section: Any, fallback_index: int = 0) -> StructuredListSection | None:
    """Return a clean StructuredListSection for dicts or model objects."""

    if section is None:
        return None
    title = str(_value(section, "title", "") or "").strip()
    section_id = str(_value(section, "section_id", "") or _value(section, "id", "") or "").strip()
    raw_items = _value(section, "items", ()) or ()
    items = tuple(item for item in (normalize_structured_list_item(raw) for raw in raw_items) if item and item.label)
    if not title or not items:
        return None
    return StructuredListSection(
        section_id=section_id or f"section_{fallback_index + 1}",
        title=title,
        items=items,
    )


def normalize_structured_list_sections(sections: Any) -> tuple[StructuredListSection, ...]:
    """Normalize renderer input while preserving section/item structure."""

    return tuple(
        section
        for section in (
            normalize_structured_list_section(raw_section, index)
            for index, raw_section in enumerate(sections or [])
        )
        if section is not None
    )


def structured_sections_to_dicts(sections: Any) -> list[dict[str, Any]]:
    """Return the legacy list-of-dicts shape without flattening list items."""

    normalized = normalize_structured_list_sections(sections)
    return [
        {
            "section_id": section.section_id,
            "title": section.title,
            "items": [
                {
                    "label": item.label,
                    "detail_lines": list(item.detail_lines),
                    "source_row_ids": list(item.source_row_ids),
                    "category": item.category,
                }
                for item in section.items
            ],
        }
        for section in normalized
    ]

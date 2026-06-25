"""Shared QA report row/text helpers."""

from __future__ import annotations

from typing import Any, Mapping

from itinerary_generation.common import get_row_type
from itinerary_generation.render_text_helpers import list_to_text
from itinerary_generation.titles import create_client_activity_title
from shared.source_rows import clean_text, edit_row_id, source_text


def _clean(value: Any) -> str:
    return clean_text(value)


def _block_text(value: Any, *, limit: int = 800) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _row_id(row: Mapping[str, Any], fallback_index: int = 0) -> str:
    return edit_row_id(row, fallback_index)


def _source_text(row: Mapping[str, Any] | None) -> str:
    text = source_text(
        row,
        ("source_text", "raw_text", "description_raw", "original_text", "input_text"),
        separator=" ",
        first_non_empty=True,
        limit=800,
    )
    if text:
        return text
    return _block_text(source_text(row, ("original_title", "title"), separator=" ", first_non_empty=True))


def _product_family(row: Mapping[str, Any]) -> str:
    fingerprint = row.get("activity_product") if isinstance(row.get("activity_product"), Mapping) else {}
    return str(
        row.get("canonical_family")
        or fingerprint.get("canonical_family")
        or row.get("product_family")
        or ""
    ).strip()


def _event_action(field: str, row_type: str = "") -> str:
    if field == "title":
        return "Review source fidelity and product fingerprinting for this item."
    if field in {"client_description", "intro", "blocks_html"}:
        return "Review the generated wording for missing, over-generic, or incorrect client-facing text."
    if field in {"includes_text", "whats_included", "whats_not_included"}:
        return "Review inclusion/exclusion extraction and optional-status handling."
    if row_type.lower() in {"activity", "cruise", "ferry"}:
        return "Review activity normalization and supplier product matching."
    return "Review why the generated value needed a manual edit."


def _row_generated_value(row: Mapping[str, Any], field: str) -> str:
    row_type = get_row_type(dict(row))
    if field == "title":
        return create_client_activity_title(dict(row)) if row_type == "Activity" else str(row.get("title", ""))
    if field == "includes_text":
        return list_to_text(row.get("includes", []))
    if field == "notable_sights_text":
        return list_to_text(row.get("notable_sights", []))
    return str(row.get(field, ""))

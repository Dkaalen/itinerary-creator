"""Structured/render document preparation for itinerary render context."""

from __future__ import annotations

from typing import Any

from itinerary_generation.editor_page_contract import hidden_page_ids, page_order_from_draft, stable_page_id
from itinerary_generation.render_document_builder import build_render_document_from_document, grouped_days_with_day_optional_rows
from itinerary_generation.structured_builder import build_itinerary_document


def build_render_context_documents(
    parsed_rows,
    grouped_days,
    output_edits: dict[str, Any],
    editor_draft: dict[str, Any],
    *,
    structured_document=None,
    render_document_builder=build_render_document_from_document,
) -> dict[str, Any]:
    """Build structured/render documents and apply hidden-page filtering."""

    page_hidden_ids = hidden_page_ids(editor_draft.get("document_pages") if isinstance(editor_draft, dict) else [])
    if structured_document is None:
        structured_document = build_itinerary_document(parsed_rows, grouped_days)
    render_grouped_days = grouped_days_with_day_optional_rows(grouped_days, parsed_rows)
    render_grouped_days = {
        str(day): rows
        for day, rows in (render_grouped_days or {}).items()
        if stable_page_id("day", day) not in page_hidden_ids
    }
    render_document = render_document_builder(
        structured_document,
        parsed_rows,
        grouped_days,
        output_edits=output_edits,
    )
    render_document.days = [
        day
        for day in (render_document.days or [])
        if stable_page_id("day", getattr(day, "day", "")) not in page_hidden_ids
    ]
    render_document.hidden_page_ids = sorted(page_hidden_ids)
    render_document.page_order = page_order_from_draft(editor_draft)
    return {
        "hidden_page_ids": page_hidden_ids,
        "structured_document": structured_document,
        "render_grouped_days": render_grouped_days,
        "render_document": render_document,
    }


__all__ = ["build_render_context_documents"]

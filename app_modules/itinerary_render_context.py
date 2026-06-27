"""Shared itinerary render-context coordinator for HTML and PDF outputs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app_modules.render_context_cover import build_render_cover
from app_modules.render_context_cover_data import _safe_label, build_cover_context_data
from app_modules.render_context_document import build_render_context_documents
from app_modules.render_context_final_data import build_final_context_data
from app_modules.render_context_final_sections import build_final_sections_for_pdf
from app_modules.render_context_summary import build_render_summary
from app_modules.render_context_summary_data import build_summary_context_data
from itinerary_generation.client_sanitizer import sanitize_render_document_client_output
from itinerary_generation.editor_page_contract import (
    final_section_is_hidden as contract_final_section_is_hidden,
    manual_pages_from_draft as contract_manual_pages_from_draft,
    page_is_hidden as contract_page_is_hidden,
    page_order_from_draft as contract_page_order_from_draft,
)
from itinerary_generation.render_document_builder import build_render_document_from_document
from itinerary_generation.render_model import RenderDocument
from itinerary_generation.render_page_order import render_page_order_with_editor_request, sorted_render_days
from itinerary_generation.structured_builder import build_itinerary_document


@dataclass(slots=True)
class ItineraryRenderContext:
    parsed_rows: list[dict]
    grouped_days: dict[str, list[dict]]
    output_edits: dict[str, Any]
    editor_draft: dict[str, Any]
    structured_document: Any
    render_grouped_days: dict[str, list[dict]]
    render_document: RenderDocument
    output_brand: str
    brand_logo_data_uri: str
    preset_name: str
    colors: dict[str, str]
    colors_json: str
    cover_theme: dict[str, Any]
    cover_kicker: str
    cover_route_label: str
    cover_title_class: str
    trip_title: str
    trip_subtitle: str
    trip_subtitle_html: str
    trip_dates: str
    cover_background_data_uri: str
    cover_background_path: str
    cover_crop_focus: str
    summary_background_data_uri: str
    summary_background_path: str
    summary_crop_focus: str
    destinations_line: str
    destinations_line_html: str
    trip_glance_title: str
    trip_glance: dict[str, str]
    journey_arc_title: str
    journey_arc_columns: dict[str, str]
    journey_arc: list[dict[str, str]]
    categorized_inclusions: Any
    manual_whats_included: list[str]
    whats_included: list[str]
    optional_addons: list[str]
    whats_not_included: list[str]
    structured_whats_not_included: Any
    typed_inclusion_pages: list[str]
    typed_inclusions_owned: bool
    saved_inclusion_pages_refreshable: bool
    typed_exclusion_html: str
    typed_exclusions_owned: bool
    saved_exclusion_html_refreshable: bool
    important_travel_notes: list[str] | str
    final_section_titles: dict[str, str]
    manual_pages: list[dict[str, Any]]
    hidden_page_ids: set[str]


def _page_is_hidden(context: ItineraryRenderContext, page_id: str) -> bool:
    return contract_page_is_hidden(context.hidden_page_ids, page_id)


def _final_section_is_hidden(context: ItineraryRenderContext, section_id: str) -> bool:
    return contract_final_section_is_hidden(context.hidden_page_ids, section_id)


def _page_order_from_draft(editor_draft: dict[str, Any]) -> list[str]:
    """Compatibility wrapper for older tests/imports."""

    return contract_page_order_from_draft(editor_draft)


def _manual_pages_from_draft(editor_draft: dict[str, Any], hidden_ids: set[str]) -> list[dict[str, Any]]:
    """Compatibility wrapper for older tests/imports."""

    return contract_manual_pages_from_draft(editor_draft, hidden_ids)


def _attach_pdf_contract(context: ItineraryRenderContext) -> None:
    context.render_document.cover = build_render_cover(context)
    context.render_document.summary = build_render_summary(context)
    context.render_document.final_sections = build_final_sections_for_pdf(context)
    context.render_document.hidden_page_ids = sorted(context.hidden_page_ids or set())
    context.render_document.days = sorted_render_days(context.render_document.days)
    context.render_document.page_order = render_page_order_with_editor_request(
        context.render_document,
        getattr(context.render_document, "page_order", []) or [],
    )


def _build_render_document_from_structured_document(structured_document, parsed_rows, grouped_days, output_edits):
    return build_render_document_from_document(
        structured_document,
        parsed_rows,
        grouped_days,
        output_edits=output_edits,
    )


def build_itinerary_render_context(parsed_rows, grouped_days, output_edits=None) -> ItineraryRenderContext:
    """Build the shared preview/PDF render context from parsed itinerary data."""

    output_edits = output_edits or {}
    editor_draft = output_edits.get("editor_draft") if isinstance(output_edits, dict) else {}
    editor_draft = editor_draft if isinstance(editor_draft, dict) else {}

    structured_document = build_itinerary_document(parsed_rows, grouped_days)
    document_data = build_render_context_documents(
        parsed_rows,
        grouped_days,
        output_edits,
        editor_draft,
        structured_document=structured_document,
        render_document_builder=_build_render_document_from_structured_document,
    )
    cover_data = build_cover_context_data(parsed_rows, grouped_days, output_edits, editor_draft)
    summary_data = build_summary_context_data(parsed_rows, grouped_days, output_edits, editor_draft)
    final_data = build_final_context_data(
        parsed_rows,
        grouped_days,
        output_edits,
        editor_draft,
        document_data["structured_document"],
    )

    context = ItineraryRenderContext(
        parsed_rows=list(parsed_rows or []),
        grouped_days=grouped_days or {},
        output_edits=output_edits,
        editor_draft=editor_draft,
        structured_document=document_data["structured_document"],
        render_grouped_days=document_data["render_grouped_days"],
        render_document=document_data["render_document"],
        manual_pages=contract_manual_pages_from_draft(editor_draft, document_data["hidden_page_ids"]),
        hidden_page_ids=document_data["hidden_page_ids"],
        **cover_data,
        **summary_data,
        **final_data,
    )
    _attach_pdf_contract(context)
    sanitize_render_document_client_output(context.render_document)
    return context


__all__ = [
    "ItineraryRenderContext",
    "_attach_pdf_contract",
    "_final_section_is_hidden",
    "_manual_pages_from_draft",
    "_page_is_hidden",
    "_page_order_from_draft",
    "_safe_label",
    "build_itinerary_render_context",
    "_build_render_document_from_structured_document",
]

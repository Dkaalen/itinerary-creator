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
from app_modules.render_final_sections_html import render_final_page_inner_html
from app_modules.presentation_language import presentation_labels, presentation_language_from_output_edits
from itinerary_generation.client_output_quality_gate import evaluate_prepared_client_output_quality
from itinerary_generation.client_quality_report import ClientOutputQualityGateReport
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
from itinerary_generation.structured_html_audit import validate_source_aware_html_coverage


@dataclass(slots=True)
class ItineraryRenderContext:
    parsed_rows: list[dict]
    grouped_days: dict[str, list[dict]]
    output_edits: dict[str, Any]
    editor_draft: dict[str, Any]
    structured_document: Any
    render_grouped_days: dict[str, list[dict]]
    render_document: RenderDocument
    editor_render_document: RenderDocument
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
    presentation_language: str
    presentation_labels: dict[str, str]
    continuity_report: Any
    client_quality_report: ClientOutputQualityGateReport | None = None


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


def _attach_document_contract(
    context: ItineraryRenderContext,
    render_document: RenderDocument,
    *,
    include_hidden: bool,
) -> None:
    render_document.presentation_language = context.presentation_language
    render_document.labels = dict(context.presentation_labels)
    for render_day in render_document.days or []:
        render_day.day_label_prefix = context.presentation_labels.get("day", "DAY")
        render_day.labels = {**dict(context.presentation_labels), **dict(render_day.labels or {})}
        for block in render_day.blocks or []:
            block.labels = {**dict(context.presentation_labels), **dict(block.labels or {})}
        for block in render_day.generated_blocks or []:
            block.labels = {**dict(context.presentation_labels), **dict(block.labels or {})}
    render_document.cover = build_render_cover(context, include_hidden=include_hidden)
    render_document.summary = build_render_summary(context, include_hidden=include_hidden)
    render_document.final_sections = build_final_sections_for_pdf(context, include_hidden=include_hidden)
    render_document.hidden_page_ids = sorted(context.hidden_page_ids or set())
    render_document.days = sorted_render_days(render_document.days)
    render_document.page_order = render_page_order_with_editor_request(
        render_document,
        getattr(render_document, "page_order", []) or [],
    )


def _attach_pdf_contract(context: ItineraryRenderContext) -> None:
    _attach_document_contract(context, context.render_document, include_hidden=False)
    _attach_document_contract(context, context.editor_render_document, include_hidden=True)


def _final_section_html_fragments(render_document: RenderDocument, section_id: str) -> list[str]:
    section = next(
        (item for item in render_document.final_sections or [] if str(item.section_id) == str(section_id)),
        None,
    )
    if section is None:
        return []
    pages = list(section.pages or [])
    if not pages and (section.content_html or section.sections or section.items or section.paragraphs):
        from itinerary_generation.render_model import RenderFinalPage

        pages = [
            RenderFinalPage(
                content_html=section.content_html,
                sections=list(section.sections or []),
                items=list(section.items or []),
                paragraphs=list(section.paragraphs or []),
            )
        ]
    return [render_final_page_inner_html(section, page) for page in pages]


def _attach_final_page_source_warnings(context: ItineraryRenderContext) -> None:
    inclusion_html_is_edited = bool(
        context.typed_inclusions_owned
        or (
            (context.output_edits.get("whats_included_pages_html") or context.output_edits.get("whats_included_html"))
            and not context.saved_inclusion_pages_refreshable
        )
    )
    exclusion_html_is_edited = bool(
        context.typed_exclusions_owned
        or (
            context.output_edits.get("whats_not_included_html")
            and not context.saved_exclusion_html_refreshable
        )
    )

    warnings = (
        *(
            validate_source_aware_html_coverage(
                html_fragments=_final_section_html_fragments(context.editor_render_document, "whats_included"),
                sections=context.structured_document.inclusions,
                page_name="What's included",
                warning_code="edited_inclusions_missing_source_identity",
            )
            if inclusion_html_is_edited
            else ()
        ),
        *(
            validate_source_aware_html_coverage(
                html_fragments=_final_section_html_fragments(context.editor_render_document, "whats_not_included"),
                sections=context.structured_document.exclusions,
                page_name="What's not included",
                warning_code="edited_exclusions_missing_source_identity",
            )
            if exclusion_html_is_edited
            else ()
        ),
    )
    if not warnings:
        return
    existing = tuple(context.structured_document.warnings or ())
    keys = {(item.code, item.message, tuple(item.source_row_ids)) for item in existing}
    additions = tuple(
        item for item in warnings
        if (item.code, item.message, tuple(item.source_row_ids)) not in keys
    )
    context.structured_document.warnings = tuple((*existing, *additions))
    messages = [item.message for item in additions]
    context.render_document.warnings = list(dict.fromkeys([*context.render_document.warnings, *messages]))
    context.editor_render_document.warnings = list(dict.fromkeys([*context.editor_render_document.warnings, *messages]))


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
    language_code = presentation_language_from_output_edits(output_edits)
    labels = presentation_labels(language_code).labels
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
    summary_data = build_summary_context_data(
        parsed_rows, grouped_days, output_edits, editor_draft,
        continuity_report=structured_document.continuity_report,
    )
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
        editor_render_document=document_data["editor_render_document"],
        manual_pages=contract_manual_pages_from_draft(editor_draft, document_data["hidden_page_ids"]),
        hidden_page_ids=document_data["hidden_page_ids"],
        presentation_language=language_code,
        presentation_labels=dict(labels),
        continuity_report=document_data["structured_document"].continuity_report,
        **cover_data,
        **summary_data,
        **final_data,
    )
    _attach_pdf_contract(context)
    _attach_final_page_source_warnings(context)
    sanitize_render_document_client_output(context.render_document)
    sanitize_render_document_client_output(context.editor_render_document)
    context.client_quality_report = evaluate_prepared_client_output_quality(
        context.render_document,
        source_rows=context.parsed_rows,
    )
    return context


__all__ = [
    "ItineraryRenderContext",
    "_attach_document_contract",
    "_attach_final_page_source_warnings",
    "_attach_pdf_contract",
    "_final_section_is_hidden",
    "_manual_pages_from_draft",
    "_page_is_hidden",
    "_page_order_from_draft",
    "_safe_label",
    "build_itinerary_render_context",
    "_build_render_document_from_structured_document",
]

"""Shared itinerary render context for HTML and PDF outputs.

The preview and PDF exporter should derive from the same typed render contract.
This module centralizes the non-UI decisions that used to be duplicated around
``build_itinerary_html`` so the PDF path can consume ``RenderDocument`` directly
without scraping the generated preview HTML for day content.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app_modules.display_settings import get_color_preset, get_color_preset_name
from itinerary_generation.cover_route import clean_or_create_cover_route_line, cover_route_html
from itinerary_generation.cover_theme import get_cover_theme
from itinerary_generation.cover_assets import resolve_cover_background
from itinerary_generation.date_resolver import get_trip_date_range_text
from itinerary_generation.editable_draft import section_by_id
from itinerary_generation.editor_page_contract import (
    final_section_is_hidden as contract_final_section_is_hidden,
    hidden_page_ids,
    manual_pages_from_draft as contract_manual_pages_from_draft,
    page_is_hidden as contract_page_is_hidden,
    page_order_from_draft as contract_page_order_from_draft,
    stable_page_id,
)
from itinerary_generation.inclusions import create_whats_included, create_whats_not_included
from itinerary_generation.render_document_builder import build_render_document_from_document, grouped_days_with_day_optional_rows
from itinerary_generation.render_model import (
    RenderCover,
    RenderDocument,
    RenderFinalPage,
    RenderFinalSection,
    RenderMetaLine,
    RenderSection,
    RenderSummary,
)
from itinerary_generation.structured_builder import build_itinerary_document
from itinerary_generation.structured_rendering import normalize_structured_list_sections
from itinerary_generation.summaries import create_journey_arc, create_trip_glance, sanitize_journey_arc_experience
from itinerary_generation.titles import create_destinations_line, create_trip_subtitle, create_trip_title
from ui.final_pages import create_optional_addons, get_important_travel_notes
from ui.inclusion_pages import paginate_categorized_inclusions
from ui.picture_workflow import pictures_are_added
from ui.render_helpers import text_to_list
from itinerary_generation.client_sanitizer import (
    normalize_important_note_paragraphs,
    sanitize_client_list,
    sanitize_client_text,
    sanitize_render_document_client_output,
)
from app_modules.itinerary_html_sections import balanced_cover_subtitle_html
from app_modules.render_context_cover import build_render_cover
from app_modules.render_context_final_sections import build_final_sections_for_pdf
from app_modules.render_context_summary import build_render_summary


@dataclass(slots=True)
class ItineraryRenderContext:
    parsed_rows: list[dict]
    grouped_days: dict[str, list[dict]]
    output_edits: dict[str, Any]
    editor_draft: dict[str, Any]
    structured_document: Any
    render_grouped_days: dict[str, list[dict]]
    render_document: RenderDocument
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
    typed_exclusion_html: str
    typed_exclusions_owned: bool
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



def _safe_label(value: Any, fallback: str) -> str:
    text = str(value or "").strip()
    return text or fallback




def _attach_pdf_contract(context: ItineraryRenderContext) -> None:
    context.render_document.cover = build_render_cover(context)
    context.render_document.summary = build_render_summary(context)
    context.render_document.final_sections = build_final_sections_for_pdf(context)
    context.render_document.hidden_page_ids = sorted(context.hidden_page_ids or set())
    context.render_document.page_order = contract_page_order_from_draft(context.editor_draft)


def build_itinerary_render_context(parsed_rows, grouped_days, output_edits=None) -> ItineraryRenderContext:
    output_edits = output_edits or {}
    editor_draft = output_edits.get("editor_draft") if isinstance(output_edits, dict) else {}
    editor_draft = editor_draft if isinstance(editor_draft, dict) else {}
    page_hidden_ids = hidden_page_ids(editor_draft.get("document_pages") if isinstance(editor_draft, dict) else [])

    structured_document = build_itinerary_document(parsed_rows, grouped_days)
    render_grouped_days = grouped_days_with_day_optional_rows(grouped_days, parsed_rows)
    render_grouped_days = {
        str(day): rows
        for day, rows in (render_grouped_days or {}).items()
        if stable_page_id("day", day) not in page_hidden_ids
    }
    render_document = build_render_document_from_document(
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
    render_document.page_order = contract_page_order_from_draft(editor_draft)

    preset_name = get_color_preset_name(output_edits)
    colors = get_color_preset(output_edits)

    include_picture_data = pictures_are_added(output_edits)
    cover_theme = get_cover_theme(parsed_rows, output_edits, include_image_data=include_picture_data)
    summary_image = resolve_cover_background(parsed_rows, output_edits, key="summary_image", include_image_data=include_picture_data)
    typed_cover = editor_draft.get("cover", {}) if isinstance(editor_draft.get("cover"), dict) else {}
    typed_summary = editor_draft.get("summary", {}) if isinstance(editor_draft.get("summary"), dict) else {}

    cover_kicker = typed_cover.get("cover_kicker") or output_edits.get("cover_kicker") or "Travel Itinerary"
    cover_route_label = _safe_label(typed_cover.get("route_label") or output_edits.get("route_label"), "Route")
    trip_title = typed_cover.get("trip_title") or output_edits.get("trip_title") or create_trip_title(parsed_rows, grouped_days)
    cover_title_class = "cover-title"
    if len(str(trip_title)) <= 24:
        cover_title_class += " cover-title-fit"
    elif len(str(trip_title)) <= 32:
        cover_title_class += " cover-title-balanced"
    trip_subtitle = typed_cover.get("trip_subtitle") or output_edits.get("trip_subtitle") or create_trip_subtitle(parsed_rows, grouped_days)
    trip_subtitle_html = balanced_cover_subtitle_html(trip_subtitle)
    trip_dates = typed_cover.get("trip_dates") or output_edits.get("trip_dates") or get_trip_date_range_text(parsed_rows)
    cover_background_data_uri = cover_theme.get("background_data_uri", "")
    cover_background_path = cover_theme.get("background_path", "")
    cover_crop_focus = cover_theme.get("background_crop_focus", "top")
    summary_background_data_uri = summary_image.get("data_uri", "")
    summary_background_path = summary_image.get("path", "")
    summary_crop_focus = summary_image.get("crop_focus", "top")
    saved_destinations_line = typed_cover.get("destinations_line") or output_edits.get("destinations_line")
    destinations_line = clean_or_create_cover_route_line(parsed_rows, saved_destinations_line or create_destinations_line(parsed_rows))
    destinations_line_html = cover_route_html(destinations_line)

    trip_glance_title = _safe_label(typed_summary.get("trip_glance_title") or output_edits.get("trip_glance_title"), "Your Trip at a Glance")
    journey_arc_title = _safe_label(typed_summary.get("journey_arc_title") or output_edits.get("journey_arc_title"), "Your Journey Arc")
    raw_arc_columns = typed_summary.get("journey_arc_columns") if isinstance(typed_summary.get("journey_arc_columns"), dict) else output_edits.get("journey_arc_columns")
    raw_arc_columns = raw_arc_columns if isinstance(raw_arc_columns, dict) else {}
    journey_arc_columns = {
        "chapter": _safe_label(raw_arc_columns.get("chapter"), "Chapter"),
        "days": _safe_label(raw_arc_columns.get("days"), "Days"),
        "experience": _safe_label(raw_arc_columns.get("experience"), "What You’ll Experience"),
    }

    trip_glance = create_trip_glance(parsed_rows, grouped_days)
    saved_trip_glance = typed_summary.get("trip_glance") or output_edits.get("trip_glance") or {}
    if isinstance(saved_trip_glance, dict):
        for label, value in saved_trip_glance.items():
            if label in trip_glance:
                trip_glance[label] = value
    # Route ownership is not a manual free-text field: these values must match
    # the overnight-stay model so old generated junk cannot survive in drafts.
    generated_trip_glance = create_trip_glance(parsed_rows, grouped_days)
    for route_label in ("Start", "End", "Destinations"):
        if route_label in generated_trip_glance:
            trip_glance[route_label] = generated_trip_glance[route_label]

    saved_journey_arc = typed_summary.get("journey_arc") or output_edits.get("journey_arc")
    weak_arc_markers = ("onward flight", "onward travel", "onward train", "onward connection", "flight connection", "travel continues", "aurora")
    if isinstance(saved_journey_arc, list) and saved_journey_arc and not any(
        any(marker in str(row.get("experience", "")).lower() for marker in weak_arc_markers)
        for row in saved_journey_arc
        if isinstance(row, dict)
    ):
        journey_arc = [
            {
                "chapter": str(row.get("chapter", "")).strip(),
                "days": str(row.get("days", "")).strip(),
                "experience": sanitize_journey_arc_experience(row.get("experience", ""), chapter=row.get("chapter", "")),
            }
            for row in saved_journey_arc
            if isinstance(row, dict)
        ]
    else:
        journey_arc = create_journey_arc(grouped_days)

    manual_whats_included = sanitize_client_list(text_to_list(output_edits.get("whats_included_text", "")))
    categorized_inclusions = structured_document.inclusions
    whats_included = manual_whats_included or create_whats_included(parsed_rows, grouped_days)
    optional_addons = create_optional_addons(parsed_rows)
    if output_edits.get("whats_not_included_text"):
        whats_not_included = sanitize_client_list(text_to_list(output_edits.get("whats_not_included_text")))
    else:
        whats_not_included = create_whats_not_included(parsed_rows)
    structured_whats_not_included = structured_document.exclusions

    typed_inclusions = section_by_id(editor_draft, "whats_included")
    typed_exclusions = section_by_id(editor_draft, "whats_not_included")
    typed_notes = section_by_id(editor_draft, "important_travel_notes")
    final_section_titles = {
        "whats_included": _safe_label(typed_inclusions.get("title") if typed_inclusions else output_edits.get("whats_included_title"), "What’s included"),
        "whats_not_included": _safe_label(typed_exclusions.get("title") if typed_exclusions else output_edits.get("whats_not_included_title"), "What’s not included"),
        "important_travel_notes": _safe_label(typed_notes.get("title") if typed_notes else output_edits.get("important_travel_notes_title"), "Important travel notes"),
        "optional_experiences": _safe_label(output_edits.get("optional_experiences_title"), "Optional Experiences"),
    }
    typed_inclusions_owned = bool(typed_inclusions)
    typed_exclusions_owned = bool(typed_exclusions)
    typed_inclusion_pages = [page.get("content_html", "") for page in typed_inclusions.get("pages", []) if isinstance(page, dict)] if typed_inclusions else []
    typed_exclusion_html = typed_exclusions.get("content_html", "") if typed_exclusions else ""
    if typed_exclusions and not typed_exclusion_html and typed_exclusions.get("pages"):
        first_page = typed_exclusions.get("pages", [{}])[0]
        typed_exclusion_html = first_page.get("content_html", "") if isinstance(first_page, dict) else ""
    important_travel_notes = normalize_important_note_paragraphs(typed_notes.get("text") if typed_notes else get_important_travel_notes(output_edits))
    manual_pages = contract_manual_pages_from_draft(editor_draft, page_hidden_ids)

    context = ItineraryRenderContext(
        parsed_rows=list(parsed_rows or []),
        grouped_days=grouped_days or {},
        output_edits=output_edits,
        editor_draft=editor_draft,
        structured_document=structured_document,
        render_grouped_days=render_grouped_days,
        render_document=render_document,
        preset_name=preset_name,
        colors=colors,
        colors_json="",
        cover_theme=cover_theme,
        cover_kicker=cover_kicker,
        cover_route_label=cover_route_label,
        cover_title_class=cover_title_class,
        trip_title=trip_title,
        trip_subtitle=trip_subtitle,
        trip_subtitle_html=trip_subtitle_html,
        trip_dates=trip_dates,
        cover_background_data_uri=cover_background_data_uri,
        cover_background_path=cover_background_path,
        cover_crop_focus=cover_crop_focus,
        summary_background_data_uri=summary_background_data_uri,
        summary_background_path=summary_background_path,
        summary_crop_focus=summary_crop_focus,
        destinations_line=destinations_line,
        destinations_line_html=destinations_line_html,
        trip_glance_title=trip_glance_title,
        trip_glance=trip_glance,
        journey_arc_title=journey_arc_title,
        journey_arc_columns=journey_arc_columns,
        journey_arc=journey_arc,
        categorized_inclusions=categorized_inclusions,
        manual_whats_included=manual_whats_included,
        whats_included=whats_included,
        optional_addons=optional_addons,
        whats_not_included=whats_not_included,
        structured_whats_not_included=structured_whats_not_included,
        typed_inclusion_pages=typed_inclusion_pages,
        typed_inclusions_owned=typed_inclusions_owned,
        typed_exclusion_html=typed_exclusion_html,
        typed_exclusions_owned=typed_exclusions_owned,
        important_travel_notes=important_travel_notes,
        final_section_titles=final_section_titles,
        manual_pages=manual_pages,
        hidden_page_ids=page_hidden_ids,
    )
    _attach_pdf_contract(context)
    sanitize_render_document_client_output(context.render_document)
    return context

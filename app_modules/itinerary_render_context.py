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
from itinerary_generation.date_resolver import get_trip_date_range_text
from itinerary_generation.editable_draft import section_by_id
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
from itinerary_generation.summaries import create_journey_arc, create_trip_glance
from itinerary_generation.titles import create_destinations_line, create_trip_subtitle, create_trip_title
from ui.final_pages import create_optional_addons, get_important_travel_notes
from ui.inclusion_pages import paginate_categorized_inclusions
from ui.picture_workflow import pictures_are_added
from ui.render_helpers import text_to_list
from app_modules.itinerary_html_sections import balanced_cover_subtitle_html


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
    cover_title_class: str
    trip_title: str
    trip_subtitle: str
    trip_subtitle_html: str
    trip_dates: str
    cover_background_data_uri: str
    cover_background_path: str
    destinations_line: str
    destinations_line_html: str
    trip_glance: dict[str, str]
    journey_arc: list[dict[str, str]]
    categorized_inclusions: Any
    manual_whats_included: list[str]
    whats_included: list[str]
    optional_addons: list[str]
    whats_not_included: list[str]
    structured_whats_not_included: Any
    typed_inclusion_pages: list[str]
    typed_exclusion_html: str
    important_travel_notes: str


def _structured_sections_to_render_sections(sections: Any) -> list[RenderSection]:
    render_sections: list[RenderSection] = []
    for section in normalize_structured_list_sections(sections):
        items: list[str] = []
        for item in section.items:
            lines = [item.label, *item.detail_lines]
            items.append("\n".join(line for line in lines if line))
        if items:
            render_sections.append(RenderSection(section.title, items))
    return render_sections


def _paginated_structured_final_pages(sections: Any) -> list[RenderFinalPage]:
    pages: list[RenderFinalPage] = []
    for page_sections in paginate_categorized_inclusions(sections):
        render_sections = _structured_sections_to_render_sections(page_sections)
        if render_sections:
            pages.append(RenderFinalPage(sections=render_sections))
    return pages


def _split_list_final_pages(items: list[str], *, items_per_page: int = 24) -> list[RenderFinalPage]:
    clean_items = [str(item or "").strip() for item in items or [] if str(item or "").strip()]
    return [RenderFinalPage(items=clean_items[index:index + items_per_page]) for index in range(0, len(clean_items), items_per_page)]


def _paragraph_final_pages(text: str) -> list[RenderFinalPage]:
    paragraphs = [item.strip() for item in str(text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n") if item.strip()]
    return [RenderFinalPage(paragraphs=paragraphs)] if paragraphs else []


def _html_final_pages(page_htmls: list[str] | str) -> list[RenderFinalPage]:
    values = page_htmls if isinstance(page_htmls, list) else [page_htmls]
    return [RenderFinalPage(content_html=str(value or "")) for value in values if str(value or "").strip()]


def _build_final_sections_for_pdf(context: ItineraryRenderContext) -> list[RenderFinalSection]:
    sections: list[RenderFinalSection] = []

    if context.typed_inclusion_pages:
        sections.append(RenderFinalSection("whats_included", "What’s included", pages=_html_final_pages(context.typed_inclusion_pages), css_class="categorized-inclusions-page"))
    elif context.output_edits.get("whats_included_pages_html"):
        sections.append(RenderFinalSection("whats_included", "What’s included", pages=_html_final_pages(context.output_edits.get("whats_included_pages_html")), css_class="categorized-inclusions-page"))
    elif context.output_edits.get("whats_included_html"):
        sections.append(RenderFinalSection("whats_included", "What’s included", pages=_html_final_pages(context.output_edits.get("whats_included_html")), css_class="categorized-inclusions-page"))
    elif context.manual_whats_included:
        sections.append(RenderFinalSection("whats_included", "What’s included", pages=_split_list_final_pages(context.whats_included)))
    else:
        sections.append(RenderFinalSection("whats_included", "What’s included", pages=_paginated_structured_final_pages(context.categorized_inclusions), css_class="categorized-inclusions-page"))

    if context.optional_addons:
        optional_pages = []
        for index in range(0, len(context.optional_addons), 8):
            page_items = []
            for addon in context.optional_addons[index:index + 8]:
                if not isinstance(addon, dict):
                    continue
                heading_bits = [str(addon.get("title", "")).strip(), str(addon.get("date", "")).strip()]
                heading = " - ".join(bit for bit in heading_bits if bit)
                details = []
                if addon.get("time"):
                    details.append(f'Time: {addon["time"]}')
                if addon.get("duration"):
                    details.append(f'Duration: {addon["duration"]}')
                if addon.get("meeting_point"):
                    details.append(f'{addon.get("meeting_label") or "Meeting point"}: {addon["meeting_point"]}')
                if addon.get("description"):
                    details.append(str(addon.get("description", "")))
                elif addon.get("includes"):
                    details.append("Includes " + ", ".join(str(item) for item in addon.get("includes") or [] if str(item).strip()))
                else:
                    details.append("Available as an optional experience.")
                page_items.append("\n".join([heading, *[detail for detail in details if detail]]))
            if page_items:
                optional_pages.append(RenderFinalPage(items=page_items))
        if optional_pages:
            sections.append(RenderFinalSection("optional_experiences", "Optional Experiences", pages=optional_pages, css_class="optional-addons-page"))

    if context.typed_exclusion_html:
        sections.append(RenderFinalSection("whats_not_included", "What’s not included", pages=_html_final_pages(context.typed_exclusion_html), css_class="categorized-exclusions-page"))
    elif context.output_edits.get("whats_not_included_html"):
        sections.append(RenderFinalSection("whats_not_included", "What’s not included", pages=_html_final_pages(context.output_edits.get("whats_not_included_html")), css_class="categorized-exclusions-page"))
    elif context.output_edits.get("whats_not_included_text"):
        sections.append(RenderFinalSection("whats_not_included", "What’s not included", pages=_split_list_final_pages(context.whats_not_included)))
    else:
        sections.append(RenderFinalSection("whats_not_included", "What’s not included", pages=_paginated_structured_final_pages(context.structured_whats_not_included), css_class="categorized-exclusions-page"))

    notes_pages = _paragraph_final_pages(context.important_travel_notes)
    if notes_pages:
        sections.append(RenderFinalSection("important_travel_notes", "Important travel notes", pages=notes_pages, css_class="important-notes-page"))

    return [section for section in sections if section.pages or section.sections or section.items or section.paragraphs or section.content_html]


def _attach_pdf_contract(context: ItineraryRenderContext) -> None:
    cover = RenderCover(
        kicker=context.cover_kicker,
        title=context.trip_title,
        subtitle=context.trip_subtitle,
        dates=context.trip_dates,
        route=context.destinations_line,
        background_path=context.cover_background_path,
        ink=str(context.cover_theme.get("ink", "")),
        muted=str(context.cover_theme.get("muted", "")),
        accent=str(context.cover_theme.get("accent", "")),
        season=str(context.cover_theme.get("season", "")),
    )
    summary = RenderSummary(
        trip_glance=[RenderMetaLine(str(label), str(value)) for label, value in context.trip_glance.items()],
        journey_arc=[
            {
                "chapter": str(row.get("chapter", "")).strip(),
                "days": str(row.get("days", "")).strip(),
                "experience": str(row.get("experience", "")).strip(),
            }
            for row in context.journey_arc
            if isinstance(row, dict)
        ],
        background_path=str(context.cover_theme.get("background_path", "")),
    )
    context.render_document.cover = cover
    context.render_document.summary = summary
    context.render_document.final_sections = _build_final_sections_for_pdf(context)


def build_itinerary_render_context(parsed_rows, grouped_days, output_edits=None) -> ItineraryRenderContext:
    output_edits = output_edits or {}
    editor_draft = output_edits.get("editor_draft") if isinstance(output_edits, dict) else {}
    editor_draft = editor_draft if isinstance(editor_draft, dict) else {}

    structured_document = build_itinerary_document(parsed_rows, grouped_days)
    render_grouped_days = grouped_days_with_day_optional_rows(grouped_days, parsed_rows)
    render_document = build_render_document_from_document(
        structured_document,
        parsed_rows,
        grouped_days,
        output_edits=output_edits,
    )

    preset_name = get_color_preset_name(output_edits)
    colors = get_color_preset(output_edits)

    cover_theme = get_cover_theme(parsed_rows, output_edits, include_image_data=pictures_are_added(output_edits))
    typed_cover = editor_draft.get("cover", {}) if isinstance(editor_draft.get("cover"), dict) else {}
    typed_summary = editor_draft.get("summary", {}) if isinstance(editor_draft.get("summary"), dict) else {}

    cover_kicker = typed_cover.get("cover_kicker") or output_edits.get("cover_kicker") or "Travel Itinerary"
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
    saved_destinations_line = typed_cover.get("destinations_line") or output_edits.get("destinations_line")
    destinations_line = clean_or_create_cover_route_line(parsed_rows, saved_destinations_line or create_destinations_line(parsed_rows))
    destinations_line_html = cover_route_html(destinations_line)

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
    weak_arc_markers = ("onward flight and accommodation", "onward travel and accommodation", "onward travel")
    if isinstance(saved_journey_arc, list) and saved_journey_arc and not any(
        any(marker in str(row.get("experience", "")).lower() for marker in weak_arc_markers)
        for row in saved_journey_arc
        if isinstance(row, dict)
    ):
        journey_arc = [
            {
                "chapter": str(row.get("chapter", "")).strip(),
                "days": str(row.get("days", "")).strip(),
                "experience": str(row.get("experience", "")).strip(),
            }
            for row in saved_journey_arc
            if isinstance(row, dict)
        ]
    else:
        journey_arc = create_journey_arc(grouped_days)

    manual_whats_included = text_to_list(output_edits.get("whats_included_text", ""))
    categorized_inclusions = structured_document.inclusions
    whats_included = manual_whats_included or create_whats_included(parsed_rows, grouped_days)
    optional_addons = create_optional_addons(parsed_rows)
    if output_edits.get("whats_not_included_text"):
        whats_not_included = text_to_list(output_edits.get("whats_not_included_text"))
    else:
        whats_not_included = create_whats_not_included(parsed_rows)
    structured_whats_not_included = structured_document.exclusions

    typed_inclusions = section_by_id(editor_draft, "whats_included")
    typed_exclusions = section_by_id(editor_draft, "whats_not_included")
    typed_notes = section_by_id(editor_draft, "important_travel_notes")
    typed_inclusion_pages = [page.get("content_html", "") for page in typed_inclusions.get("pages", []) if isinstance(page, dict)] if typed_inclusions else []
    typed_exclusion_html = typed_exclusions.get("content_html", "") if typed_exclusions else ""
    if typed_exclusions and not typed_exclusion_html and typed_exclusions.get("pages"):
        first_page = typed_exclusions.get("pages", [{}])[0]
        typed_exclusion_html = first_page.get("content_html", "") if isinstance(first_page, dict) else ""
    important_travel_notes = typed_notes.get("text") if typed_notes else get_important_travel_notes(output_edits)

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
        cover_title_class=cover_title_class,
        trip_title=trip_title,
        trip_subtitle=trip_subtitle,
        trip_subtitle_html=trip_subtitle_html,
        trip_dates=trip_dates,
        cover_background_data_uri=cover_background_data_uri,
        cover_background_path=cover_background_path,
        destinations_line=destinations_line,
        destinations_line_html=destinations_line_html,
        trip_glance=trip_glance,
        journey_arc=journey_arc,
        categorized_inclusions=categorized_inclusions,
        manual_whats_included=manual_whats_included,
        whats_included=whats_included,
        optional_addons=optional_addons,
        whats_not_included=whats_not_included,
        structured_whats_not_included=structured_whats_not_included,
        typed_inclusion_pages=typed_inclusion_pages,
        typed_exclusion_html=typed_exclusion_html,
        important_travel_notes=important_travel_notes,
    )
    _attach_pdf_contract(context)
    return context

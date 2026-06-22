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
from itinerary_generation.editor_page_contract import final_section_page_id, hidden_page_ids, stable_page_id
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
    cover_crop_focus: str
    summary_background_data_uri: str
    summary_background_path: str
    summary_crop_focus: str
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
    typed_inclusions_owned: bool
    typed_exclusion_html: str
    typed_exclusions_owned: bool
    important_travel_notes: list[str] | str
    manual_pages: list[dict[str, Any]]
    hidden_page_ids: set[str]


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
    clean_items = sanitize_client_list(items or [])
    return [RenderFinalPage(items=clean_items[index:index + items_per_page]) for index in range(0, len(clean_items), items_per_page)]


def _paragraph_final_pages(text: Any) -> list[RenderFinalPage]:
    """Build clean paragraph pages without stringifying lists or line fragments."""

    paragraphs = normalize_important_note_paragraphs(text)
    return [RenderFinalPage(paragraphs=paragraphs)] if paragraphs else []


def _html_final_pages(page_htmls: list[str] | str) -> list[RenderFinalPage]:
    values = page_htmls if isinstance(page_htmls, list) else [page_htmls]
    return [RenderFinalPage(content_html=str(value or "")) for value in values if str(value or "").strip()]


def _page_is_hidden(context: ItineraryRenderContext, page_id: str) -> bool:
    return str(page_id or "") in (context.hidden_page_ids or set())


def _final_section_is_hidden(context: ItineraryRenderContext, section_id: str) -> bool:
    return _page_is_hidden(context, final_section_page_id(section_id))


def _manual_pages_from_draft(editor_draft: dict[str, Any], hidden_ids: set[str]) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    raw_pages = editor_draft.get("document_pages") if isinstance(editor_draft, dict) else []
    if not isinstance(raw_pages, (list, tuple)):
        return pages
    for page in raw_pages:
        if not isinstance(page, dict) or page.get("page_type") != "manual":
            continue
        page_id = str(page.get("page_id") or "").strip()
        if page_id in hidden_ids:
            continue
        blocks = page.get("manual_blocks") if isinstance(page.get("manual_blocks"), (list, tuple)) else []
        content_parts: list[str] = []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            fields = block.get("editable_fields") if isinstance(block.get("editable_fields"), dict) else {}
            html = str(fields.get("content_html") or "").strip()
            if html:
                content_parts.append(html)
        pages.append({
            "page_id": page_id,
            "title": str(page.get("title") or "Custom page").strip() or "Custom page",
            "content_html": "".join(content_parts),
            "sort_order": int(page.get("sort_order") or 0),
        })
    return sorted(pages, key=lambda page: int(page.get("sort_order") or 0))


def _build_final_sections_for_pdf(context: ItineraryRenderContext) -> list[RenderFinalSection]:
    sections: list[RenderFinalSection] = []

    if not _final_section_is_hidden(context, "whats_included") and context.typed_inclusions_owned:
        if context.typed_inclusion_pages:
            sections.append(RenderFinalSection("whats_included", "What’s included", pages=_html_final_pages(context.typed_inclusion_pages), css_class="categorized-inclusions-page"))
    elif not _final_section_is_hidden(context, "whats_included") and context.output_edits.get("whats_included_pages_html"):
        sections.append(RenderFinalSection("whats_included", "What’s included", pages=_html_final_pages(context.output_edits.get("whats_included_pages_html")), css_class="categorized-inclusions-page"))
    elif not _final_section_is_hidden(context, "whats_included") and context.output_edits.get("whats_included_html"):
        sections.append(RenderFinalSection("whats_included", "What’s included", pages=_html_final_pages(context.output_edits.get("whats_included_html")), css_class="categorized-inclusions-page"))
    elif not _final_section_is_hidden(context, "whats_included") and context.manual_whats_included:
        sections.append(RenderFinalSection("whats_included", "What’s included", pages=_split_list_final_pages(context.whats_included)))
    elif not _final_section_is_hidden(context, "whats_included"):
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
                page_items.append("\n".join(sanitize_client_list([heading, *[detail for detail in details if detail]])))
            if page_items:
                optional_pages.append(RenderFinalPage(items=page_items))
        if optional_pages:
            sections.append(RenderFinalSection("optional_experiences", "Optional Experiences", pages=optional_pages, css_class="optional-addons-page"))

    if not _final_section_is_hidden(context, "whats_not_included") and context.typed_exclusions_owned:
        if context.typed_exclusion_html:
            sections.append(RenderFinalSection("whats_not_included", "What’s not included", pages=_html_final_pages(context.typed_exclusion_html), css_class="categorized-exclusions-page"))
    elif not _final_section_is_hidden(context, "whats_not_included") and context.output_edits.get("whats_not_included_html"):
        sections.append(RenderFinalSection("whats_not_included", "What’s not included", pages=_html_final_pages(context.output_edits.get("whats_not_included_html")), css_class="categorized-exclusions-page"))
    elif not _final_section_is_hidden(context, "whats_not_included") and context.output_edits.get("whats_not_included_text"):
        sections.append(RenderFinalSection("whats_not_included", "What’s not included", pages=_split_list_final_pages(context.whats_not_included)))
    elif not _final_section_is_hidden(context, "whats_not_included"):
        sections.append(RenderFinalSection("whats_not_included", "What’s not included", pages=_paginated_structured_final_pages(context.structured_whats_not_included), css_class="categorized-exclusions-page"))

    notes_pages = _paragraph_final_pages(context.important_travel_notes)
    if notes_pages and not _final_section_is_hidden(context, "important_travel_notes"):
        sections.append(RenderFinalSection("important_travel_notes", "Important travel notes", pages=notes_pages, css_class="important-notes-page"))

    for page in context.manual_pages:
        html = str(page.get("content_html") or "").strip()
        if html:
            sections.append(RenderFinalSection(
                str(page.get("page_id") or "manual_page"),
                str(page.get("title") or "Custom page"),
                pages=_html_final_pages(html),
                css_class="manual-page",
            ))

    return [section for section in sections if section.pages or section.sections or section.items or section.paragraphs or section.content_html]


def _attach_pdf_contract(context: ItineraryRenderContext) -> None:
    cover = RenderCover(
        kicker=context.cover_kicker,
        title=context.trip_title,
        subtitle=context.trip_subtitle,
        dates=context.trip_dates,
        route=context.destinations_line,
        background_path=context.cover_background_path,
        crop_focus=context.cover_crop_focus,
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
                "experience": sanitize_journey_arc_experience(row.get("experience", ""), chapter=row.get("chapter", "")),
            }
            for row in context.journey_arc
            if isinstance(row, dict)
        ],
        background_path=context.summary_background_path,
        crop_focus=context.summary_crop_focus,
    )
    context.render_document.cover = None if _page_is_hidden(context, "cover") else cover
    context.render_document.summary = None if _page_is_hidden(context, "summary") else summary
    context.render_document.final_sections = _build_final_sections_for_pdf(context)
    context.render_document.hidden_page_ids = sorted(context.hidden_page_ids or set())


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

    preset_name = get_color_preset_name(output_edits)
    colors = get_color_preset(output_edits)

    include_picture_data = pictures_are_added(output_edits)
    cover_theme = get_cover_theme(parsed_rows, output_edits, include_image_data=include_picture_data)
    summary_image = resolve_cover_background(parsed_rows, output_edits, key="summary_image", include_image_data=include_picture_data)
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
    cover_crop_focus = cover_theme.get("background_crop_focus", "top")
    summary_background_data_uri = summary_image.get("data_uri", "")
    summary_background_path = summary_image.get("path", "")
    summary_crop_focus = summary_image.get("crop_focus", "top")
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
    typed_inclusions_owned = bool(typed_inclusions)
    typed_exclusions_owned = bool(typed_exclusions)
    typed_inclusion_pages = [page.get("content_html", "") for page in typed_inclusions.get("pages", []) if isinstance(page, dict)] if typed_inclusions else []
    typed_exclusion_html = typed_exclusions.get("content_html", "") if typed_exclusions else ""
    if typed_exclusions and not typed_exclusion_html and typed_exclusions.get("pages"):
        first_page = typed_exclusions.get("pages", [{}])[0]
        typed_exclusion_html = first_page.get("content_html", "") if isinstance(first_page, dict) else ""
    important_travel_notes = normalize_important_note_paragraphs(typed_notes.get("text") if typed_notes else get_important_travel_notes(output_edits))
    manual_pages = _manual_pages_from_draft(editor_draft, page_hidden_ids)

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
        cover_crop_focus=cover_crop_focus,
        summary_background_data_uri=summary_background_data_uri,
        summary_background_path=summary_background_path,
        summary_crop_focus=summary_crop_focus,
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
        typed_inclusions_owned=typed_inclusions_owned,
        typed_exclusion_html=typed_exclusion_html,
        typed_exclusions_owned=typed_exclusions_owned,
        important_travel_notes=important_travel_notes,
        manual_pages=manual_pages,
        hidden_page_ids=page_hidden_ids,
    )
    _attach_pdf_contract(context)
    sanitize_render_document_client_output(context.render_document)
    return context

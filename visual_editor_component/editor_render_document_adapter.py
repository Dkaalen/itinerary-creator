"""Adapt the canonical render contract to the visual-editor payload shape.

The editor owns editing metadata and image controls, but it must not regenerate
client-facing itinerary content.  Titles, introductions, day blocks, cover,
summary and final sections are projected from the prepared RenderDocument.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from app_modules.render_final_sections_html import render_final_page_inner_html
from itinerary_generation.cover_route import clean_or_create_cover_route_line
from itinerary_generation.date_resolver import get_trip_date_range_text
from itinerary_generation.editable_draft import day_by_id
from itinerary_generation.inclusions import create_whats_not_included
from itinerary_generation.render_model import RenderDocument, RenderFinalPage, RenderFinalSection
from itinerary_generation.summaries import create_journey_arc, create_trip_glance
from itinerary_generation.titles import create_destinations_line, create_trip_subtitle, create_trip_title
from ui.inclusion_pages import render_inclusion_page_inner_htmls, render_inclusion_sections_inner_html
from ui.render_blocks import render_blocks_to_html
from ui.render_helpers import list_to_text


def _section_pages(section: RenderFinalSection) -> list[RenderFinalPage]:
    pages = list(section.pages or [])
    if pages:
        return pages
    if section.content_html or section.sections or section.items or section.paragraphs:
        return [
            RenderFinalPage(
                content_html=section.content_html,
                sections=list(section.sections or []),
                items=list(section.items or []),
                paragraphs=list(section.paragraphs or []),
            )
        ]
    return []


def _section_page_htmls(section: RenderFinalSection | None) -> list[dict[str, str]]:
    if section is None:
        return []
    return [
        {"html": html}
        for page in _section_pages(section)
        if (html := render_final_page_inner_html(section, page)).strip()
    ]


def _section_text(section: RenderFinalSection | None) -> str:
    if section is None:
        return ""
    lines: list[str] = []
    for page in _section_pages(section):
        lines.extend(str(item).strip() for item in page.items or [] if str(item).strip())
        lines.extend(str(item).strip() for item in page.paragraphs or [] if str(item).strip())
        for structured in page.sections or []:
            lines.extend(str(item).strip() for item in structured.items or [] if str(item).strip())
    return list_to_text(lines)


def build_cover_payload_from_render_document(
    render_document: RenderDocument,
    *,
    cover_theme: Mapping[str, Any],
    cover_image: Mapping[str, Any],
    summary_image: Mapping[str, Any],
) -> dict[str, Any]:
    cover = render_document.cover
    if cover is None:
        return {}
    return {
        "cover_kicker": cover.kicker,
        "route_label": cover.route_label,
        "cover_season": cover.season or str(cover_theme.get("season") or "summer"),
        "cover_background_data_uri": str(cover_image.get("data_uri") or cover_theme.get("background_data_uri") or ""),
        "cover_image": deepcopy(dict(cover_image)),
        "summary_image": deepcopy(dict(summary_image)),
        "cover_ink": cover.ink or str(cover_theme.get("ink") or "#1f3446"),
        "cover_muted": cover.muted or str(cover_theme.get("muted") or "#7b746c"),
        "cover_accent": cover.accent or str(cover_theme.get("accent") or "#b89555"),
        "trip_title": cover.title,
        "trip_subtitle": cover.subtitle,
        "trip_dates": cover.dates,
        "destinations_line": cover.route,
    }


def build_summary_payload_from_render_document(render_document: RenderDocument) -> dict[str, Any]:
    summary = render_document.summary
    if summary is None:
        return {}
    return {
        "trip_glance_title": summary.trip_glance_title,
        "journey_arc_title": summary.journey_arc_title,
        "journey_arc_columns": dict(summary.journey_arc_columns or {}),
        "trip_glance": {str(item.label): str(item.value) for item in summary.trip_glance or []},
        "journey_arc": [dict(row) for row in summary.journey_arc or [] if isinstance(row, dict)],
    }


def build_day_payloads_from_render_document(
    render_document: RenderDocument,
    stored_editor_draft: Mapping[str, Any],
    *,
    day_images: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    payload_days: list[dict[str, Any]] = []
    generated_days: list[dict[str, Any]] = []
    for render_day in render_document.days or []:
        day_id = str(render_day.day)
        typed_day = day_by_id(dict(stored_editor_draft), day_id)
        blocks_html = render_blocks_to_html(list(render_day.blocks or []))
        generated_blocks_html = render_blocks_to_html(list(render_day.generated_blocks or render_day.blocks or []))
        image = deepcopy(dict(day_images.get(day_id) or {}))
        payload_days.append(
            {
                "day": day_id,
                "label": typed_day.get("label") or day_id,
                "date": render_day.date,
                "title": render_day.title,
                "city": render_day.city,
                "intro": render_day.intro,
                "intro_generated_value": render_day.generated_intro,
                "intro_generator_version": render_day.intro_generator_version,
                "intro_source_signature": render_day.intro_source_signature,
                "intro_manual_override": bool(render_day.intro_manual_override),
                "blocks_html": blocks_html,
                "blocks_html_generated_value": generated_blocks_html,
                "blocks_html_generator_version": render_day.blocks_generator_version,
                "blocks_manual_override": bool(render_day.blocks_manual_override),
                "blocks": typed_day.get("blocks")
                or [{"block_id": "main", "kind": "day_content", "content_html": blocks_html}],
                "image": image,
                "source_row_ids": list(render_day.source_row_ids or []),
            }
        )
        generated_days.append(
            {
                "day": day_id,
                "label": day_id,
                "date": render_day.generated_date,
                "title": render_day.generated_title,
                "city": render_day.generated_city,
                "intro": render_day.generated_intro,
                "blocks_html": generated_blocks_html,
            }
        )
    return payload_days, generated_days


def build_final_pages_payload_from_render_document(render_document: RenderDocument) -> dict[str, Any]:
    sections = {str(section.section_id): section for section in render_document.final_sections or []}
    included = sections.get("whats_included")
    excluded = sections.get("whats_not_included")
    notes = sections.get("important_travel_notes")
    included_pages = _section_page_htmls(included)
    excluded_pages = _section_page_htmls(excluded)
    notes_pages = _section_page_htmls(notes)
    return {
        "whats_included_title": included.title if included else "What’s included",
        "whats_not_included_title": excluded.title if excluded else "What’s not included",
        "important_travel_notes_title": notes.title if notes else "Important travel notes",
        "whats_included_html": "".join(page["html"] for page in included_pages),
        "whats_included_pages_html": included_pages,
        "whats_included_text": _section_text(included),
        "whats_not_included_html": "".join(page["html"] for page in excluded_pages),
        "whats_not_included_text": _section_text(excluded),
        "important_travel_notes_text": _section_text(notes),
        "important_travel_notes_html": "".join(page["html"] for page in notes_pages),
    }


def build_generated_values_from_render_context(context: Any, generated_days: list[dict[str, Any]]) -> dict[str, Any]:
    """Build reset baselines from already-prepared source and structured facts."""

    parsed_rows = context.parsed_rows
    grouped_days = context.grouped_days
    structured = context.structured_document
    generated_inclusion_pages = render_inclusion_page_inner_htmls(structured.inclusions)
    generated_exclusions_html = render_inclusion_sections_inner_html(structured.exclusions)
    return {
        "cover": {
            "cover_kicker": "Travel Itinerary",
            "route_label": "Route",
            "trip_title": create_trip_title(parsed_rows, grouped_days),
            "trip_subtitle": create_trip_subtitle(parsed_rows, grouped_days),
            "trip_dates": get_trip_date_range_text(parsed_rows),
            "destinations_line": clean_or_create_cover_route_line(parsed_rows, create_destinations_line(parsed_rows)),
        },
        "summary": {
            "trip_glance_title": "Your Trip at a Glance",
            "journey_arc_title": "How Your Trip Unfolds",
            "journey_arc_columns": {"chapter": "Chapter", "days": "Days", "experience": "What You’ll Experience"},
            "trip_glance": create_trip_glance(parsed_rows, grouped_days),
            "journey_arc": create_journey_arc(grouped_days),
        },
        "days": generated_days,
        "final_pages": {
            "whats_included_title": "What’s included",
            "whats_not_included_title": "What’s not included",
            "important_travel_notes_title": "Important travel notes",
            "whats_included_html": render_inclusion_sections_inner_html(structured.inclusions),
            "whats_included_pages_html": [
                {"html": str(page.get("html") if isinstance(page, dict) else page or "")}
                for page in generated_inclusion_pages
            ],
            "whats_not_included_html": generated_exclusions_html,
            "whats_not_included_text": list_to_text(create_whats_not_included(parsed_rows)),
            "important_travel_notes_text": "",
            "important_travel_notes_html": "",
        },
    }


__all__ = [
    "build_cover_payload_from_render_document",
    "build_day_payloads_from_render_document",
    "build_final_pages_payload_from_render_document",
    "build_generated_values_from_render_context",
    "build_summary_payload_from_render_document",
]

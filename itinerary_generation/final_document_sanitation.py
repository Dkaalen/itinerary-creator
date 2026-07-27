"""Canonical final sanitation of a prepared :class:`RenderDocument`.

This is the third sanitation stage.  It traverses only the prepared render
contract and delegates field semantics to ``field_sanitation``.  It does not
classify rows, calculate continuity, rewrite facts, or touch technical metadata.
"""

from __future__ import annotations

from typing import Any

from itinerary_domain.field_sanitation import (
    CustomerField,
    is_unresolved_customer_value,
    sanitize_customer_field,
    sanitize_customer_html,
    sanitize_customer_list,
)
from itinerary_generation.render_model import (
    RenderBlock,
    RenderCover,
    RenderDay,
    RenderDocument,
    RenderFinalPage,
    RenderFinalSection,
    RenderMetaLine,
    RenderSection,
    RenderSummary,
)


def _meta_value_field(label: str) -> CustomerField:
    lower = str(label or "").casefold()
    if "time" in lower or "duration" in lower:
        return CustomerField.TIME
    if any(marker in lower for marker in ("meeting", "pick-up", "pickup", "drop-off", "dropoff")):
        return CustomerField.MEETING_POINT
    if any(marker in lower for marker in ("location", "route", "departure", "arrival", "destination")):
        return CustomerField.LOCATION
    return CustomerField.DESCRIPTION


def _sanitize_meta(values: Any) -> list[RenderMetaLine]:
    result: list[RenderMetaLine] = []
    seen: set[tuple[str, str]] = set()
    for line in values or []:
        if not isinstance(line, RenderMetaLine):
            continue
        label = sanitize_customer_field(line.label, CustomerField.TITLE)
        value = sanitize_customer_field(line.value, _meta_value_field(label))
        if not label or is_unresolved_customer_value(value):
            continue
        key = (label.casefold(), value.casefold())
        if key not in seen:
            result.append(RenderMetaLine(label, value))
            seen.add(key)
    return result


def _sanitize_section(value: RenderSection, item_field: CustomerField) -> RenderSection:
    value.title = sanitize_customer_field(value.title, CustomerField.TITLE)
    value.items = sanitize_customer_list(value.items, item_field)
    return value


def _sanitize_block(value: RenderBlock) -> RenderBlock:
    value.section_title = sanitize_customer_field(value.section_title, CustomerField.TITLE)
    value.title = sanitize_customer_field(value.title, CustomerField.TITLE)
    value.meta = _sanitize_meta(value.meta)
    value.includes = sanitize_customer_list(value.includes, CustomerField.INCLUSION)
    value.description = sanitize_customer_field(value.description, CustomerField.DESCRIPTION)
    value.content_html = sanitize_customer_html(value.content_html, CustomerField.DESCRIPTION)
    value.notable_sights = sanitize_customer_list(value.notable_sights, CustomerField.LOCATION)
    value.lines = sanitize_customer_list(value.lines, CustomerField.DESCRIPTION)
    value.extra_sections = [_sanitize_section(item, CustomerField.DESCRIPTION) for item in value.extra_sections or []]
    return value


def _sanitize_day(value: RenderDay) -> RenderDay:
    value.city = sanitize_customer_field(value.city, CustomerField.LOCATION)
    value.title = sanitize_customer_field(value.title, CustomerField.TITLE)
    value.intro = sanitize_customer_field(value.intro, CustomerField.DESCRIPTION)
    value.date = sanitize_customer_field(value.date, CustomerField.DESCRIPTION)
    value.blocks = [_sanitize_block(item) for item in value.blocks or []]
    value.generated_city = sanitize_customer_field(value.generated_city, CustomerField.LOCATION)
    value.generated_title = sanitize_customer_field(value.generated_title, CustomerField.TITLE)
    value.generated_intro = sanitize_customer_field(value.generated_intro, CustomerField.DESCRIPTION)
    value.generated_date = sanitize_customer_field(value.generated_date, CustomerField.DESCRIPTION)
    value.generated_blocks = [_sanitize_block(item) for item in value.generated_blocks or []]
    return value


def _final_item_field(section_id: str) -> CustomerField:
    if section_id == "whats_included":
        return CustomerField.INCLUSION
    if section_id == "whats_not_included":
        return CustomerField.EXCLUSION
    return CustomerField.DESCRIPTION


def _sanitize_final_page(value: RenderFinalPage, item_field: CustomerField) -> RenderFinalPage:
    value.sections = [_sanitize_section(item, item_field) for item in value.sections or []]
    value.items = sanitize_customer_list(value.items, item_field)
    value.paragraphs = sanitize_customer_list(value.paragraphs, CustomerField.DESCRIPTION)
    value.content_html = sanitize_customer_html(value.content_html, item_field)
    return value


def _sanitize_final_section(value: RenderFinalSection) -> RenderFinalSection:
    item_field = _final_item_field(str(value.section_id or ""))
    value.title = sanitize_customer_field(value.title, CustomerField.TITLE)
    value.pages = [_sanitize_final_page(item, item_field) for item in value.pages or []]
    value.sections = [_sanitize_section(item, item_field) for item in value.sections or []]
    value.items = sanitize_customer_list(value.items, item_field)
    value.paragraphs = sanitize_customer_list(value.paragraphs, CustomerField.DESCRIPTION)
    value.content_html = sanitize_customer_html(value.content_html, item_field)
    return value


def sanitize_prepared_render_document(render_document: Any) -> Any:
    """Sanitize one prepared document in place and return the same object.

    Technical fields such as row ids, source ids, warnings, labels, continuity,
    page order, hidden-page ids, CSS classes, metadata, and image state are not
    traversed or rewritten.
    """

    if not isinstance(render_document, RenderDocument):
        return render_document

    render_document.title = sanitize_customer_field(render_document.title, CustomerField.TITLE)
    render_document.subtitle = sanitize_customer_field(render_document.subtitle, CustomerField.DESCRIPTION)
    render_document.route = sanitize_customer_field(render_document.route, CustomerField.LOCATION)
    render_document.days = [_sanitize_day(item) for item in render_document.days or []]

    if isinstance(render_document.cover, RenderCover):
        cover = render_document.cover
        cover.kicker = sanitize_customer_field(cover.kicker, CustomerField.TITLE)
        cover.route_label = sanitize_customer_field(cover.route_label, CustomerField.TITLE)
        cover.title = sanitize_customer_field(cover.title, CustomerField.TITLE)
        cover.subtitle = sanitize_customer_field(cover.subtitle, CustomerField.DESCRIPTION)
        cover.dates = sanitize_customer_field(cover.dates, CustomerField.DESCRIPTION)
        cover.route = sanitize_customer_field(cover.route, CustomerField.LOCATION)
        cover.season = sanitize_customer_field(cover.season, CustomerField.DESCRIPTION)

    if isinstance(render_document.summary, RenderSummary):
        summary = render_document.summary
        summary.trip_glance_title = sanitize_customer_field(summary.trip_glance_title, CustomerField.TITLE)
        summary.trip_glance = _sanitize_meta(summary.trip_glance)
        summary.journey_arc_title = sanitize_customer_field(summary.journey_arc_title, CustomerField.TITLE)
        summary.journey_arc_columns = {
            str(key): sanitize_customer_field(value, CustomerField.TITLE)
            for key, value in (summary.journey_arc_columns or {}).items()
        }
        sanitized_arc: list[dict[str, str]] = []
        for row in summary.journey_arc or []:
            if not isinstance(row, dict):
                continue
            sanitized_row: dict[str, str] = {}
            for key, value in row.items():
                cleaned = sanitize_customer_field(value, CustomerField.DESCRIPTION)
                if cleaned:
                    sanitized_row[str(key)] = cleaned
            if sanitized_row:
                sanitized_arc.append(sanitized_row)
        summary.journey_arc = sanitized_arc

    render_document.final_sections = [_sanitize_final_section(item) for item in render_document.final_sections or []]
    return render_document


__all__ = ["sanitize_prepared_render_document"]

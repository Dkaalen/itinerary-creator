"""Extract only customer-visible text from prepared render documents.

Quality checks audit the sanitized ``RenderDocument`` contract.  They do not
walk technical dataclass fields such as provenance, source row identities,
continuity reports, image paths, warnings, labels, CSS classes, or editor state.
"""

from __future__ import annotations

from typing import Any, Mapping


def append_text(parts: list[str], value: Any) -> None:
    """Append textual values selected by an explicit customer-visible traversal."""

    if value is None:
        return
    if isinstance(value, str):
        if value.strip():
            parts.append(value)
        return
    if isinstance(value, Mapping):
        for item in value.values():
            append_text(parts, item)
        return
    if isinstance(value, (list, tuple, set)):
        for item in value:
            append_text(parts, item)


def _append_meta(parts: list[str], values: Any) -> None:
    for line in values or []:
        append_text(parts, getattr(line, "label", ""))
        append_text(parts, getattr(line, "value", ""))


def _append_sections(parts: list[str], values: Any) -> None:
    for section in values or []:
        append_text(parts, getattr(section, "title", ""))
        append_text(parts, getattr(section, "items", []))


def _append_block(parts: list[str], block: Any) -> None:
    append_text(parts, getattr(block, "section_title", ""))
    append_text(parts, getattr(block, "title", ""))
    _append_meta(parts, getattr(block, "meta", []))
    append_text(parts, getattr(block, "includes", []))
    append_text(parts, getattr(block, "description", ""))
    append_text(parts, getattr(block, "content_html", ""))
    append_text(parts, getattr(block, "notable_sights", []))
    append_text(parts, getattr(block, "lines", []))
    _append_sections(parts, getattr(block, "extra_sections", []))


def _append_day(parts: list[str], day: Any) -> None:
    append_text(parts, getattr(day, "city", ""))
    append_text(parts, getattr(day, "title", ""))
    append_text(parts, getattr(day, "intro", ""))
    append_text(parts, getattr(day, "date", ""))
    for block in getattr(day, "blocks", []) or []:
        _append_block(parts, block)


def _append_cover(parts: list[str], cover: Any) -> None:
    if cover is None:
        return
    for name in ("kicker", "route_label", "title", "subtitle", "dates", "route", "season"):
        append_text(parts, getattr(cover, name, ""))


def _append_summary(parts: list[str], summary: Any) -> None:
    if summary is None:
        return
    append_text(parts, getattr(summary, "trip_glance_title", ""))
    _append_meta(parts, getattr(summary, "trip_glance", []))
    append_text(parts, getattr(summary, "journey_arc_title", ""))
    append_text(parts, getattr(summary, "journey_arc_columns", {}))
    append_text(parts, getattr(summary, "journey_arc", []))


def _append_final_page(parts: list[str], page: Any) -> None:
    _append_sections(parts, getattr(page, "sections", []))
    append_text(parts, getattr(page, "items", []))
    append_text(parts, getattr(page, "paragraphs", []))
    append_text(parts, getattr(page, "content_html", ""))


def _append_final_section(parts: list[str], section: Any) -> None:
    append_text(parts, getattr(section, "title", ""))
    for page in getattr(section, "pages", []) or []:
        _append_final_page(parts, page)
    _append_sections(parts, getattr(section, "sections", []))
    append_text(parts, getattr(section, "items", []))
    append_text(parts, getattr(section, "paragraphs", []))
    append_text(parts, getattr(section, "content_html", ""))


def render_document_text(render_document: Any) -> str:
    """Return customer-visible text from one prepared document."""

    parts: list[str] = []
    append_text(parts, getattr(render_document, "title", ""))
    append_text(parts, getattr(render_document, "subtitle", ""))
    append_text(parts, getattr(render_document, "route", ""))
    _append_cover(parts, getattr(render_document, "cover", None))
    _append_summary(parts, getattr(render_document, "summary", None))
    for day in getattr(render_document, "days", []) or []:
        _append_day(parts, day)
    for section in getattr(render_document, "final_sections", []) or []:
        _append_final_section(parts, section)
    return "\n".join(parts)


def raw_supplier_scan_text(render_document: Any) -> str:
    """Return customer body fields that may contain raw supplier labels.

    Canonical page and section headings such as “What’s included” are excluded
    because they are presentation labels, not supplier-field leakage.
    """

    parts: list[str] = []
    for day in getattr(render_document, "days", []) or []:
        append_text(parts, getattr(day, "title", ""))
        append_text(parts, getattr(day, "intro", ""))
        for block in getattr(day, "blocks", []) or []:
            _append_block(parts, block)
    for section in getattr(render_document, "final_sections", []) or []:
        for page in getattr(section, "pages", []) or []:
            for child in getattr(page, "sections", []) or []:
                append_text(parts, getattr(child, "items", []))
            append_text(parts, getattr(page, "items", []))
            append_text(parts, getattr(page, "paragraphs", []))
            append_text(parts, getattr(page, "content_html", ""))
        append_text(parts, getattr(section, "items", []))
        append_text(parts, getattr(section, "paragraphs", []))
        append_text(parts, getattr(section, "content_html", ""))
    return "\n".join(parts)

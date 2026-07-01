"""HTML fallback detection for the typed PDF exporter."""

from __future__ import annotations

from collections.abc import Mapping

from itinerary_generation.day_render_manual_html import manual_day_html_override
from itinerary_generation.generated_ownership import blocks_html_is_manual, html_equivalent
from itinerary_generation.render_model import RenderDocument
from pdf_exporter_modules.pdf_html_support import (
    any_html_requires_fallback,
    html_fragment_supported,
    iter_html_values,
)


def _iter_html_values(value):
    return iter_html_values(value)


def _final_content_html_supported(html_fragment: str) -> bool:
    """Return True when an edited final-page fragment can render in typed PDF."""

    return html_fragment_supported(html_fragment)


def _day_content_html_supported(html_fragment: str) -> bool:
    """Return True when an edited day-body fragment can render in typed PDF."""

    return html_fragment_supported(html_fragment)


def _any_final_html_requires_fallback(value) -> bool:
    return any_html_requires_fallback(value)


def _any_day_html_requires_fallback(value) -> bool:
    return any_html_requires_fallback(value)


def _manual_day_ids(output_edits: Mapping | None) -> set[str]:
    if not isinstance(output_edits, Mapping):
        return set()
    day_ids: set[str] = set()
    legacy_days = output_edits.get("days")
    if isinstance(legacy_days, Mapping):
        for day, day_edit in legacy_days.items():
            if isinstance(day_edit, Mapping) and blocks_html_is_manual(day_edit):
                day_ids.add(str(day))
    draft = output_edits.get("editor_draft")
    if isinstance(draft, Mapping):
        for day in draft.get("days") or []:
            if not isinstance(day, Mapping) or not blocks_html_is_manual(day):
                continue
            day_id = str(day.get("day") or day.get("day_id") or day.get("label") or "").strip()
            if day_id:
                day_ids.add(day_id)
            elif _any_day_html_requires_fallback(day.get("blocks_html", day.get("blocks"))):
                day_ids.add("")
    return day_ids


def _render_document_manual_day_html(render_document: RenderDocument, day_id: str) -> list[str]:
    html_fragments: list[str] = []
    for day in getattr(render_document, "days", []) or []:
        if str(getattr(day, "day", "") or "") != str(day_id):
            continue
        for block in getattr(day, "blocks", []) or []:
            if getattr(block, "kind", "") == "manual_day_html":
                html_fragments.append(str(getattr(block, "content_html", "") or ""))
    return html_fragments


def _manual_day_edits_require_fallback(render_document: RenderDocument, output_edits: Mapping | None) -> bool:
    for day_id in _manual_day_ids(output_edits):
        if not day_id:
            return True
        manual_html = manual_day_html_override(day_id, output_edits)
        if not manual_html.is_manual:
            continue
        if not manual_html.html.strip():
            continue
        if not _day_content_html_supported(manual_html.html):
            return True
        rendered_html = _render_document_manual_day_html(render_document, day_id)
        if not any(html_equivalent(fragment, manual_html.html) for fragment in rendered_html):
            return True
    return False


def render_document_requires_html_fallback(render_document: RenderDocument | None, output_edits: Mapping | None = None) -> bool:
    """Return True only when unsupported saved HTML still owns visible content."""

    if render_document is None:
        return True

    for section in getattr(render_document, "final_sections", []) or []:
        if _any_final_html_requires_fallback(getattr(section, "content_html", "")):
            return True
        for page in getattr(section, "pages", []) or []:
            if _any_final_html_requires_fallback(getattr(page, "content_html", "")):
                return True

    for day in getattr(render_document, "days", []) or []:
        for block in getattr(day, "blocks", []) or []:
            if getattr(block, "kind", "") == "manual_day_html" and _any_day_html_requires_fallback(getattr(block, "content_html", "")):
                return True

    edits = output_edits or {}
    if _manual_day_edits_require_fallback(render_document, edits):
        return True

    draft = edits.get("editor_draft") if isinstance(edits, Mapping) else None
    if isinstance(draft, Mapping):
        for section in draft.get("final_sections") or []:
            if not isinstance(section, Mapping):
                continue
            if _any_final_html_requires_fallback(section.get("content_html", "")):
                return True
            for page in section.get("pages") or []:
                if isinstance(page, Mapping) and _any_final_html_requires_fallback(page):
                    return True

    if not isinstance(edits, Mapping):
        return False
    legacy_html_keys = (
        "whats_included_pages_html",
        "whats_included_html",
        "whats_not_included_html",
    )
    return any(_any_final_html_requires_fallback(edits.get(key)) for key in legacy_html_keys)

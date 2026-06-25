"""HTML fallback detection for the typed PDF exporter."""

from __future__ import annotations

from collections.abc import Mapping

from bs4 import BeautifulSoup

from itinerary_generation.generated_ownership import blocks_html_is_manual
from itinerary_generation.render_model import RenderDocument

_SUPPORTED_FINAL_HTML_TAGS = {
    "b", "br", "div", "em", "i", "li", "ol", "p", "span", "strong", "ul",
}

_SUPPORTED_FINAL_HTML_CLASSES = {
    "activity-inclusion-block",
    "activity-inclusion-title",
    "body-text",
    "content-block",
    "final-list",
    "inclusion-category-block",
    "inclusion-entry-detail",
    "inclusion-entry-spacer",
    "inclusion-entry-title",
    "section-title",
    "strong-line",
    "premium-note-card",
    "premium-note-card-title",
    "premium-notes-grid",
}


def _iter_html_values(value):
    if isinstance(value, (list, tuple)):
        for item in value:
            if isinstance(item, Mapping):
                yield str(item.get("content_html") or item.get("html") or "")
            else:
                yield str(item or "")
        return
    if isinstance(value, Mapping):
        yield str(value.get("content_html") or value.get("html") or "")
        return
    yield str(value or "")


def _final_content_html_supported(html_fragment: str) -> bool:
    """Return True when an edited final-page fragment can render in typed PDF."""

    html_fragment = str(html_fragment or "").strip()
    if not html_fragment:
        return True

    soup = BeautifulSoup(html_fragment, "html.parser")
    for tag in soup.find_all(True):
        if tag.name not in _SUPPORTED_FINAL_HTML_TAGS:
            return False
        for class_name in tag.get("class") or []:
            if class_name not in _SUPPORTED_FINAL_HTML_CLASSES:
                return False
    return True


def _any_final_html_requires_fallback(value) -> bool:
    return any(
        bool(html.strip()) and not _final_content_html_supported(html)
        for html in _iter_html_values(value)
    )


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

    edits = output_edits or {}
    for day_edit in (edits.get("days") or {}).values() if isinstance(edits, Mapping) else []:
        if isinstance(day_edit, Mapping) and blocks_html_is_manual(day_edit):
            return True

    draft = edits.get("editor_draft") if isinstance(edits, Mapping) else None
    if isinstance(draft, Mapping):
        for day in draft.get("days") or []:
            if isinstance(day, Mapping) and blocks_html_is_manual(day):
                return True
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

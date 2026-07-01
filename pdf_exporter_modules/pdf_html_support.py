"""Supported editor-HTML contract for typed PDF export."""

from __future__ import annotations

from collections.abc import Mapping

from bs4 import BeautifulSoup

_SUPPORTED_HTML_TAGS = {
    "b",
    "br",
    "div",
    "em",
    "i",
    "li",
    "ol",
    "p",
    "span",
    "strong",
    "ul",
}

_SUPPORTED_HTML_CLASSES = {
    "accommodation-block",
    "activity-block",
    "activity-inclusion-block",
    "activity-inclusion-title",
    "arrival-block",
    "body-text",
    "content-block",
    "cruise-leisure-block",
    "day-overview-block",
    "departure-block",
    "detail-list",
    "final-list",
    "generic-block",
    "group-tour-day-block",
    "included-block",
    "inclusion-category-block",
    "inclusion-category-list",
    "inclusion-entry-detail",
    "inclusion-entry-spacer",
    "inclusion-entry-title",
    "inclusion-multiline-list",
    "leisure-block",
    "manual-day-html-block",
    "manual-page",
    "meta-label",
    "muted-note",
    "optional-experience-block",
    "premium-note-card",
    "premium-note-card-title",
    "premium-notes-grid",
    "section-title",
    "self-arranged-block",
    "self-transfer-block",
    "small-section",
    "strong-line",
    "transport-block",
    "travel-sequence-block",
}


def iter_html_values(value):
    """Yield HTML strings from legacy and typed edit payload shapes."""

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


def html_fragment_supported(html_fragment: str) -> bool:
    """Return True when the fragment stays inside the typed PDF HTML subset."""

    html_fragment = str(html_fragment or "").strip()
    if not html_fragment:
        return True

    soup = BeautifulSoup(html_fragment, "html.parser")
    for tag in soup.find_all(True):
        if tag.name not in _SUPPORTED_HTML_TAGS:
            return False
        for class_name in tag.get("class") or []:
            if class_name not in _SUPPORTED_HTML_CLASSES:
                return False
    return True


def any_html_requires_fallback(value) -> bool:
    """Return True when any visible fragment is outside the typed subset."""

    return any(bool(html.strip()) and not html_fragment_supported(html) for html in iter_html_values(value))


__all__ = [
    "any_html_requires_fallback",
    "html_fragment_supported",
    "iter_html_values",
]

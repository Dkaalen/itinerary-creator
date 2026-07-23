"""Client-facing text sanitizer.

This module removes supplier/commercial details that should never reach the
preview or PDF, especially prices.  It deliberately preserves the useful label
around an optional item, e.g. ``Optional Vök Baths entrance (55€/person)`` becomes
``Optional Vök Baths entrance``.
"""

from __future__ import annotations

import re
from typing import Any

from text_polish import strip_price_fragments
from itinerary_generation.clipboard_sanitizer import strip_clipboard_fragment_markers
from shared.url_metadata import strip_urls
from itinerary_generation.client_copy_sanitation import (
    is_unresolved_customer_value,
    sanitize_customer_copy_text,
    sanitize_customer_html,
)

_CURRENCY_RE = re.compile(
    r"(?:€|\$|£|\b(?:NOK|SEK|DKK|ISK|USD|EUR|GBP)\b|\bkr\b)",
    flags=re.IGNORECASE,
)

PRICE_PATTERN_RE = re.compile(
    r"(?:"
    r"(?:€|\$|£)\s*\d[\d.,]*"
    r"|\d[\d.,]*\s*(?:€|\$|£)"
    r"|\b(?:NOK|SEK|DKK|ISK|USD|EUR|GBP|kr)\s*\d[\d.,]*\b"
    r"|\b\d[\d.,]*\s*(?:NOK|SEK|DKK|ISK|USD|EUR|GBP|kr)\b"
    r"|\b\d[\d.,]*\s*/\s*(?:person|pax|passenger|adult|child)\b"
    r"|\b\d[\d.,]*\s*(?:per|pr\.)\s*(?:person|pax|passenger|adult|child)\b"
    r"|\b(?:per|pr\.)\s*(?:person|pax|passenger|adult|child)\b"
    r")",
    flags=re.IGNORECASE,
)

_PRICE_PARENTHESES_RE = re.compile(
    r"\(\s*(?:[^)]*?(?:€|\$|£|\b(?:NOK|SEK|DKK|ISK|USD|EUR|GBP|kr)\b)[^)]*?|\d[\d.,]*\s*/\s*(?:person|pax|passenger|adult|child))\s*\)",
    flags=re.IGNORECASE,
)

_COST_WORD_AMOUNT_RE = re.compile(
    r"\b(?:price|cost|fee|supplement|single\s+travell?er\s+supplement\s+fee)\s*(?:is|from|at|:)?\s*\d[\d.,]*\b",
    flags=re.IGNORECASE,
)

_EMPTY_PAREN_RE = re.compile(r"\(\s*\)")


_PRICE_BLOCKER_CONTEXT_RE = re.compile(
    r"\b(?:price|cost|fee|supplement|single\s+travell?er\s+supplement)\b",
    flags=re.IGNORECASE,
)

_BAGGAGE_ALLOWANCE_DETAIL_RE = re.compile(
    r"(?:"
    r"\b(?:checked|check(?:ed)?[ -]?in|carry[- ]?on|cabin)\b"
    r"|\b(?:bag|baggage|luggage)\b"
    r"|\b\d+\s*kg\b"
    r")",
    flags=re.IGNORECASE,
)


def _mask_safe_baggage_per_person_phrases(text: str) -> str:
    """Hide allowance-only ``per person`` wording from price/currency scanning.

    The client output can legitimately say that flight tickets include a checked
    bag and carry-on bag per person.  That wording should not be treated like a
    leaked supplier price, while price-like phrases such as ``fee 50 per
    person`` must still be caught.
    """

    if not text or "per" not in text.lower():
        return text

    def replace(match: re.Match[str]) -> str:
        start, end = match.span()
        context = text[max(0, start - 140): min(len(text), end + 40)]
        if _PRICE_BLOCKER_CONTEXT_RE.search(context):
            return match.group(0)
        detail_hits = _BAGGAGE_ALLOWANCE_DETAIL_RE.findall(context)
        if len(detail_hits) >= 2:
            return "__CLIENT_SAFE_BAGGAGE_PER_PERSON__"
        return match.group(0)

    return re.sub(r"\bper\s+person\b", replace, text, flags=re.IGNORECASE)


def contains_price_or_currency(value: object) -> bool:
    """Return True when a client-facing string still contains price/currency text."""

    text = str(value or "")
    if not text:
        return False
    scan_text = _mask_safe_baggage_per_person_phrases(text)
    return bool(PRICE_PATTERN_RE.search(scan_text) or _CURRENCY_RE.search(scan_text))


def sanitize_client_text(value: object) -> str:
    """Remove prices/currency and tidy leftover punctuation from a text value."""

    text = strip_urls(strip_clipboard_fragment_markers(value))
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if "\n" in text:
        return "\n".join(part for part in (sanitize_client_text(line) for line in text.split("\n")) if part)
    terminal = re.search(r"[.!?]\s*$", text)
    text = text.replace("\xa0", " ")
    baggage_per_person_marker = "__CLIENT_SAFE_BAGGAGE_PER_PERSON__"
    baggage_per_person = re.compile(
        r"((?:\d+\s*x\s*\d+\s*kg\s*(?:checked|check(?:ed)?[ -]?in|carry[- ]?on)|"
        r"(?:checked|carry[- ]?on|cabin)\s+(?:bag|baggage|luggage))[^.;,]{0,32})\bper\s+person\b",
        flags=re.IGNORECASE,
    )
    text = baggage_per_person.sub(lambda match: f"{match.group(1)}{baggage_per_person_marker}", text)
    text = _PRICE_PARENTHESES_RE.sub(" ", text)
    text = strip_price_fragments(text)
    text = PRICE_PATTERN_RE.sub(" ", text)
    text = _CURRENCY_RE.sub(" ", text)
    text = _COST_WORD_AMOUNT_RE.sub(lambda match: re.sub(r"\s+\d[\d.,]*\b", "", match.group(0)), text)
    text = _EMPTY_PAREN_RE.sub(" ", text)
    text = re.sub(r"\b(?:per|pr\.)\s*(?:person|pax|passenger|adult|child)\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    text = re.sub(r"(?:,\s*){2,}", ", ", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = text.replace(baggage_per_person_marker, "per person")
    text = re.sub(r"\s+and\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*,\s*and\s*$", "", text, flags=re.IGNORECASE)
    text = text.strip(" -:|,;")
    if terminal and text and not re.search(r"[.!?]$", text):
        text += terminal.group(0).strip()
    return sanitize_customer_copy_text(text)


def sanitize_client_list(values: Any) -> list[str]:
    """Return sanitized, non-empty, de-duplicated strings."""

    if values is None:
        return []
    if isinstance(values, str):
        raw_values = [values]
    else:
        raw_values = list(values or [])
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in raw_values:
        text = sanitize_client_text(value)
        key = text.lower()
        if text and key not in seen:
            cleaned.append(text)
            seen.add(key)
    return cleaned


def normalize_important_note_paragraphs(values: Any) -> list[str]:
    """Merge note fragments into real paragraphs.

    Saved editor text can arrive as one fragment per visual line.  This helper
    keeps already-clean paragraph lists intact while joining sentence fragments
    until a terminal punctuation mark is reached.
    """

    if values is None:
        return []
    if isinstance(values, str):
        pieces = [line.strip() for line in values.replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip()]
    else:
        pieces = []
        for value in values or []:
            pieces.extend(line.strip() for line in str(value or "").replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip())
    if not pieces:
        return []
    paragraphs: list[str] = []
    buffer: list[str] = []
    for piece in pieces:
        text = sanitize_client_text(piece)
        if not text:
            continue
        buffer.append(text)
        if re.search(r"[.!?]$", text):
            paragraph = " ".join(buffer)
            paragraph = re.sub(r"\s+([,.;:])", r"\1", paragraph)
            paragraph = re.sub(r"\s{2,}", " ", paragraph).strip()
            if paragraph:
                paragraphs.append(paragraph)
            buffer = []
    if buffer:
        paragraph = " ".join(buffer)
        paragraph = re.sub(r"\s+([,.;:])", r"\1", paragraph)
        paragraph = re.sub(r"\s{2,}", " ", paragraph).strip()
        if paragraph:
            paragraphs.append(paragraph)
    return paragraphs


def sanitize_render_document_client_output(render_document: Any) -> Any:
    """Sanitize only fields that are part of the client render contract."""

    from itinerary_generation.render_model import (
        RenderBlock, RenderCover, RenderDay, RenderDocument, RenderFinalPage,
        RenderFinalSection, RenderMetaLine, RenderSection, RenderSummary,
    )

    def text(value: object) -> str:
        return sanitize_client_text(value)

    def items(values: Any) -> list[str]:
        return sanitize_client_list(values)

    def meta(values: Any) -> list[RenderMetaLine]:
        result: list[RenderMetaLine] = []
        seen: set[tuple[str, str]] = set()
        for line in values or []:
            if not isinstance(line, RenderMetaLine):
                continue
            label = text(line.label)
            value = text(line.value)
            if not label or is_unresolved_customer_value(value):
                continue
            key = (label.casefold(), value.casefold())
            if key not in seen:
                result.append(RenderMetaLine(label, value))
                seen.add(key)
        return result

    def section(value: RenderSection) -> RenderSection:
        value.title = text(value.title)
        value.items = items(value.items)
        return value

    def block(value: RenderBlock) -> RenderBlock:
        value.section_title = text(value.section_title)
        value.title = text(value.title)
        value.meta = meta(value.meta)
        value.includes = items(value.includes)
        value.description = text(value.description)
        value.content_html = sanitize_customer_html(value.content_html, text_sanitizer=text)
        value.notable_sights = items(value.notable_sights)
        value.lines = items(value.lines)
        value.extra_sections = [section(item) for item in value.extra_sections or []]
        # row_id, source_row_ids, warnings, css_class and labels are technical.
        return value

    def day(value: RenderDay) -> RenderDay:
        value.city = text(value.city)
        value.title = text(value.title)
        value.intro = text(value.intro)
        value.date = text(value.date)
        value.blocks = [block(item) for item in value.blocks or []]
        return value

    def final_page(value: RenderFinalPage) -> RenderFinalPage:
        value.sections = [section(item) for item in value.sections or []]
        value.items = items(value.items)
        value.paragraphs = items(value.paragraphs)
        value.content_html = sanitize_customer_html(value.content_html, text_sanitizer=text)
        return value

    def final_section(value: RenderFinalSection) -> RenderFinalSection:
        value.title = text(value.title)
        value.pages = [final_page(item) for item in value.pages or []]
        value.sections = [section(item) for item in value.sections or []]
        value.items = items(value.items)
        value.paragraphs = items(value.paragraphs)
        value.content_html = sanitize_customer_html(value.content_html, text_sanitizer=text)
        return value

    if not isinstance(render_document, RenderDocument):
        return render_document
    render_document.title = text(render_document.title)
    render_document.subtitle = text(render_document.subtitle)
    render_document.route = text(render_document.route)
    render_document.days = [day(item) for item in render_document.days or []]
    if isinstance(render_document.cover, RenderCover):
        cover = render_document.cover
        cover.kicker = text(cover.kicker)
        cover.route_label = text(cover.route_label)
        cover.title = text(cover.title)
        cover.subtitle = text(cover.subtitle)
        cover.dates = text(cover.dates)
        cover.route = text(cover.route)
    if isinstance(render_document.summary, RenderSummary):
        summary = render_document.summary
        summary.trip_glance_title = text(summary.trip_glance_title)
        summary.trip_glance = meta(summary.trip_glance)
        summary.journey_arc_title = text(summary.journey_arc_title)
        summary.journey_arc_columns = {
            str(key): text(value) for key, value in (summary.journey_arc_columns or {}).items()
        }
        summary.journey_arc = [
            {str(key): text(value) for key, value in row.items() if text(value)}
            for row in summary.journey_arc or []
            if isinstance(row, dict)
        ]
    render_document.final_sections = [final_section(item) for item in render_document.final_sections or []]
    return render_document


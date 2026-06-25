"""Client-facing text sanitizer.

This module removes supplier/commercial details that should never reach the
preview or PDF, especially prices.  It deliberately preserves the useful label
around an optional item, e.g. ``Optional Vök Baths entrance (55€/person)`` becomes
``Optional Vök Baths entrance``.
"""

from __future__ import annotations

import re
from dataclasses import fields, is_dataclass
from typing import Any

from text_polish import strip_price_fragments
from itinerary_generation.clipboard_sanitizer import strip_clipboard_fragment_markers

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

    text = strip_clipboard_fragment_markers(value)
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
    return text


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
    """Sanitize all client-facing strings in a RenderDocument-like object in place."""

    def visit(value: Any):
        if isinstance(value, str):
            return sanitize_client_text(value)
        if isinstance(value, list):
            for index, item in enumerate(value):
                value[index] = visit(item)
            return value
        if isinstance(value, dict):
            for key, item in list(value.items()):
                value[key] = visit(item)
            return value
        if is_dataclass(value):
            for field in fields(value):
                # Do not mutate opaque metadata dictionaries aggressively unless
                # they are part of the render model traversal above.
                try:
                    setattr(value, field.name, visit(getattr(value, field.name)))
                except (AttributeError, TypeError):
                    pass
            return value
        return value

    return visit(render_document)

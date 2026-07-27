"""Field-aware sanitation for itinerary customer copy.

This is the second sanitation stage.  It cleans already extracted/generated
fields according to their semantic role without traversing render documents,
reclassifying products, or touching source metadata.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import Enum
import html
import re
from typing import Any

from bs4 import BeautifulSoup, Comment, NavigableString

from shared.clipboard_sanitizer import strip_clipboard_fragment_markers


class CustomerField(str, Enum):
    TITLE = "title"
    DESCRIPTION = "description"
    INCLUSION = "inclusion"
    EXCLUSION = "exclusion"
    MEETING_POINT = "meeting_point"
    LOCATION = "location"
    TIME = "time"
    URL_METADATA = "url_metadata"
    INTERNAL_NOTE = "internal_note"


_PLACEHOLDER_VALUE_RE = re.compile(
    r"^(?:tbd|tbc|tba|to be (?:confirmed|advised|announced|determined)|"
    r"not (?:available|confirmed)|unknown|n/?a|none|null|[-–—?]+)$",
    re.IGNORECASE,
)
_PLACEHOLDER_INLINE_RE = re.compile(
    r"\b(?:tbd|tbc|tba|to be (?:confirmed|advised|announced|determined))\b",
    re.IGNORECASE,
)
_DUPLICATE_LABEL_RE = re.compile(
    r"\b(?P<label>route|time|duration|meeting point|pick[- ]?up(?:/drop[- ]?off)?|"
    r"departure|arrival|includes?|description)\s*:\s*(?P=label)\s*:\s*",
    re.IGNORECASE,
)
_DUPLICATE_ARTICLE_RE = re.compile(r"\b(?P<article>the|a|an)(?:\s+(?P=article)){1,}\s+", re.IGNORECASE)
_EMPTY_LABEL_RE = re.compile(
    r"^(?:route|time|duration|meeting point|pick[- ]?up(?:/drop[- ]?off)?|"
    r"departure|arrival|includes?|description)\s*:\s*$",
    re.IGNORECASE,
)

_URL_RE = re.compile(r"(?:(?:https?:)?//|www\.)[^\s<>\"']+", re.IGNORECASE)
_DAMAGED_LABELLED_URL_RE = re.compile(r"(?:\s*[-–—|·]\s*)?\bURL\s*:\s*https?\s*:\s*/?\s*/?[^\n|]*(?=$|\n)", re.IGNORECASE)
_EMAIL_RE = re.compile(r"(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])", re.IGNORECASE)
_LABELLED_PHONE_RE = re.compile(
    r"\b(?:tel(?:ephone)?|phone|mobile|call|contact(?:\s+number)?)\s*[:\-]?\s*"
    r"(?:\+?\d[\d \t().-]{6,}\d)",
    re.IGNORECASE,
)
_INTERNATIONAL_PHONE_RE = re.compile(r"(?<![\w])\+\d[\d \t().-]{6,}\d(?![\w])")
_PHONE_CANDIDATE_RE = re.compile(r"(?<![\w])\d[\d \t().-]{6,}\d(?![\w])")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_YEAR_RANGE_RE = re.compile(r"^\d{4}\s*[-–—]\s*\d{4}$")
_SUPPLIER_CODE_RE = re.compile(
    r"\b(?:supplier|operator|booking|reservation|voucher|confirmation)\s*"
    r"(?:code|ref(?:erence)?|number|id)\s*[:#-]?\s*[A-Z0-9][A-Z0-9._/-]{2,}\b",
    re.IGNORECASE,
)
_COMMISSION_RE = re.compile(
    r"\b(?:commission(?:able)?|net\s+rate|gross\s+rate|markup|margin)\b"
    r"(?:\s*[:=-]?\s*[^.;\n]*)?",
    re.IGNORECASE,
)
_SUPPLIER_ADMIN_RE = re.compile(
    r"\b(?:internal (?:note|use)|supplier (?:note|reference|booking)|booking (?:reference|instruction)|"
    r"voucher (?:note|reference|instruction)|for office use|do not show|do not publish|"
    r"net rate|commission(?:able)?|contact (?:the )?(?:supplier|operator)|operator note|"
    r"reservation reference|admin(?:istrative)? note)\b",
    re.IGNORECASE,
)
_ADMIN_LINE_START_RE = re.compile(
    r"^(?:internal|supplier|booking|voucher|for office|do not|net rate|gross rate|commission|"
    r"contact (?:the )?(?:supplier|operator)|operator note|reservation reference|admin)",
    re.IGNORECASE,
)
_INLINE_ADMIN_TAIL_RE = re.compile(
    r"(?:\s*[|;]\s*|\.\s+)(?:internal|supplier|booking|voucher|for office|do not|"
    r"net rate|gross rate|commission|contact (?:the )?(?:supplier|operator)|operator note|"
    r"reservation reference|admin(?:istrative)?)\b.*$",
    re.IGNORECASE,
)
_EMPTY_BOOKING_CTA_RE = re.compile(
    r"(?:\s*[-–—|·:]\s*)?(?:book(?:\s+(?:here|online|now))?|booking\s+(?:url|link)|"
    r"website|url)\s*:?[\s.-]*$",
    re.IGNORECASE,
)
_EMPTY_CONTACT_CTA_RE = re.compile(r"^(?:contact|call)(?:\s+(?:or|and))?[.!?]*$", re.IGNORECASE)

_CURRENCY_RE = re.compile(r"(?:€|\$|£|\b(?:NOK|SEK|DKK|ISK|USD|EUR|GBP)\b|\bkr\b)", re.IGNORECASE)
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
    re.IGNORECASE,
)
_PRICE_PARENTHESES_RE = re.compile(
    r"\(\s*(?:[^)]*?(?:€|\$|£|\b(?:NOK|SEK|DKK|ISK|USD|EUR|GBP|kr)\b)[^)]*?"
    r"|\d[\d.,]*\s*/\s*(?:person|pax|passenger|adult|child))\s*\)",
    re.IGNORECASE,
)

_BAGGAGE_PER_PERSON_RE = re.compile(
    r"((?:(?:\d+\s*x\s*)?\d+\s*kg\s*(?:checked|check(?:ed)?[ -]?in|carry[- ]?on)?"
    r"[^.;]{0,48}(?:bag|baggage|luggage)?|"
    r"(?:checked|check(?:ed)?[ -]?in|carry[- ]?on|cabin)\s+(?:bag|baggage|luggage)"
    r"[^.;]{0,48}\d+\s*kg)[^.;]{0,40})\bper\s+person\b",
    re.IGNORECASE,
)
_BAGGAGE_PER_PERSON_MARKER = "__CLIENT_SAFE_BAGGAGE_PER_PERSON__"

_COST_WORD_AMOUNT_RE = re.compile(
    r"\b(?:price|cost|fee|supplement|single\s+travell?er\s+supplement\s+fee)"
    r"\s*(?:is|from|at|:)?\s*\d[\d.,]*\b",
    re.IGNORECASE,
)

_UNSAFE_BLOCK_RE = re.compile(
    r"<\s*(script|style|iframe|object|embed|template|svg|math)\b[^>]*>.*?(?:<\s*/\s*\1\s*>|$)",
    re.IGNORECASE | re.DOTALL,
)
_UNSAFE_OPEN_TAG_RE = re.compile(
    r"<\s*/?\s*(?:script|style|iframe|object|embed|template|svg|math)\b[^>]*>",
    re.IGNORECASE | re.DOTALL,
)
_ALLOWED_TAGS = {
    "a", "b", "blockquote", "br", "caption", "div", "em", "h1", "h2", "h3", "h4", "h5", "h6",
    "i", "li", "ol", "p", "section", "small", "span", "strong", "table", "tbody", "td", "th", "thead",
    "tr", "u", "ul",
}
_URL_ATTRIBUTES = {"href", "src", "srcset", "action", "formaction", "poster", "background", "xlink:href"}
_SAFE_ATTRIBUTES = {"class", "id", "title", "role"}


_FIELD_WITHOUT_PLACEHOLDERS = {
    CustomerField.TITLE,
    CustomerField.DESCRIPTION,
    CustomerField.INCLUSION,
    CustomerField.EXCLUSION,
    CustomerField.MEETING_POINT,
    CustomerField.LOCATION,
    CustomerField.TIME,
}
_CUSTOMER_FIELDS = _FIELD_WITHOUT_PLACEHOLDERS


def _as_field(field: CustomerField | str) -> CustomerField:
    return field if isinstance(field, CustomerField) else CustomerField(str(field))


def is_unresolved_customer_value(value: object) -> bool:
    text = re.sub(r"\s+", " ", str(value or "")).strip(" \t\r\n:|,;")
    return not text or bool(_PLACEHOLDER_VALUE_RE.fullmatch(text))


def _strip_urls(text: str) -> str:
    text = _DAMAGED_LABELLED_URL_RE.sub("", text)
    return _URL_RE.sub("", text)


def _strip_phone_candidate(match: re.Match[str]) -> str:
    candidate = re.sub(r"\s+", " ", match.group(0)).strip()
    compact = candidate.replace(" ", "")
    if _ISO_DATE_RE.fullmatch(compact) or _YEAR_RANGE_RE.fullmatch(candidate):
        return candidate
    digits = re.sub(r"\D", "", candidate)
    if not 8 <= len(digits) <= 15:
        return candidate
    if not re.search(r"[\s().]", candidate):
        return candidate
    return ""


def _strip_contacts(text: str) -> str:
    text = _EMAIL_RE.sub("", text)
    text = _LABELLED_PHONE_RE.sub("", text)
    text = _INTERNATIONAL_PHONE_RE.sub("", text)
    return _PHONE_CANDIDATE_RE.sub(_strip_phone_candidate, text)


def _strip_commercial_fragments(text: str) -> str:
    text = _BAGGAGE_PER_PERSON_RE.sub(
        lambda match: f"{match.group(1)}{_BAGGAGE_PER_PERSON_MARKER}",
        text,
    )
    text = _PRICE_PARENTHESES_RE.sub(" ", text)
    text = PRICE_PATTERN_RE.sub(" ", text)
    text = _CURRENCY_RE.sub(" ", text)
    text = _COST_WORD_AMOUNT_RE.sub(lambda match: re.sub(r"\s+\d[\d.,]*\b", "", match.group(0)), text)
    text = _COMMISSION_RE.sub("", text)
    text = _SUPPLIER_CODE_RE.sub("", text)
    return text.replace(_BAGGAGE_PER_PERSON_MARKER, "per person")


def _normalize_customer_line(line: str, field: CustomerField) -> str:
    if field in _CUSTOMER_FIELDS:
        line = _INLINE_ADMIN_TAIL_RE.sub("", line)
        line = _strip_urls(line)
        line = _strip_contacts(line)
        line = _strip_commercial_fragments(line)
    if field in _FIELD_WITHOUT_PLACEHOLDERS:
        line = _PLACEHOLDER_INLINE_RE.sub("", line)
    line = _DUPLICATE_LABEL_RE.sub(lambda match: f"{match.group('label').title()}: ", line)
    line = _DUPLICATE_ARTICLE_RE.sub(lambda match: f"{match.group('article')} ", line)
    line = re.sub(r"\(\s*\)", " ", line)
    line = re.sub(r"\s+([,.;:!?])", r"\1", line)
    line = re.sub(r"(?:,\s*){2,}", ", ", line)
    line = re.sub(r"([:|,;])\s*\1+", r"\1", line)
    line = re.sub(r"\.{3,}", "…", line)
    line = re.sub(r"([!?])\1+", r"\1", line)
    line = _EMPTY_BOOKING_CTA_RE.sub("", line)
    if _EMPTY_CONTACT_CTA_RE.fullmatch(line.strip()):
        return ""
    line = re.sub(r"\s{2,}", " ", line).strip(" \t:|,;")
    return line


def sanitize_customer_field(value: object, field: CustomerField | str) -> str:
    """Sanitize one field without changing its itinerary meaning.

    URL metadata and internal notes are intentionally preserved as internal
    data.  Customer-visible fields remove leakage but do not apply title case,
    synonyms, place inference, route changes, or product-name rewriting.
    """

    field = _as_field(field)
    text = html.unescape(strip_clipboard_fragment_markers(value))
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")

    if field is CustomerField.URL_METADATA:
        return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n") if line.strip())
    if field is CustomerField.INTERNAL_NOTE:
        return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n") if line.strip())

    cleaned_lines: list[str] = []
    for raw_line in text.split("\n"):
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        if _SUPPLIER_ADMIN_RE.search(line) and _ADMIN_LINE_START_RE.match(line):
            continue
        line = _normalize_customer_line(line, field)
        if not line or _EMPTY_LABEL_RE.fullmatch(line) or is_unresolved_customer_value(line):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def sanitize_customer_list(
    values: Iterable[object] | object | None,
    field: CustomerField | str,
) -> list[str]:
    if values is None:
        return []
    raw_values = [values] if isinstance(values, str) else list(values) if isinstance(values, Iterable) else [values]
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in raw_values:
        text = sanitize_customer_field(value, field)
        key = text.casefold()
        if text and key not in seen:
            cleaned.append(text)
            seen.add(key)
    return cleaned


def _attribute_is_safe(name: str, value: Any) -> bool:
    lower = name.casefold()
    if lower.startswith("on") or lower in _URL_ATTRIBUTES or lower in {"style", "contenteditable"}:
        return False
    if not (lower in _SAFE_ATTRIBUTES or lower.startswith("aria-") or lower.startswith("data-")):
        return False
    text = " ".join(str(item) for item in value) if isinstance(value, (list, tuple)) else str(value or "")
    return not bool(_URL_RE.search(text) or re.search(r"javascript\s*:", text, flags=re.IGNORECASE))


def sanitize_customer_html(value: object, field: CustomerField | str) -> str:
    """Sanitize prepared customer HTML while preserving safe source identity."""

    field = _as_field(field)
    source = str(value or "")
    if not source:
        return ""
    source = _UNSAFE_BLOCK_RE.sub("", source)
    source = _UNSAFE_OPEN_TAG_RE.sub("", source)
    soup = BeautifulSoup(source, "html.parser")

    for comment in soup.find_all(string=lambda node: isinstance(node, Comment)):
        comment.extract()
    for tag in list(soup.find_all(True)):
        name = str(tag.name or "").casefold()
        if name not in _ALLOWED_TAGS:
            tag.unwrap()
            continue
        safe_attrs = {
            attr: attr_value
            for attr, attr_value in dict(tag.attrs or {}).items()
            if _attribute_is_safe(str(attr), attr_value)
        }
        tag.attrs = safe_attrs
        if name == "a":
            tag.attrs.pop("href", None)

    for node in list(soup.find_all(string=True)):
        if not isinstance(node, NavigableString) or isinstance(node, Comment):
            continue
        cleaned = sanitize_customer_field(str(node), field)
        if cleaned:
            node.replace_with(cleaned)
        else:
            node.extract()

    return str(soup).strip()


def contains_price_or_currency(value: object) -> bool:
    text = str(value or "")
    if not text:
        return False
    scan_text = _BAGGAGE_PER_PERSON_RE.sub(
        lambda match: f"{match.group(1)}{_BAGGAGE_PER_PERSON_MARKER}",
        text,
    )
    return bool(PRICE_PATTERN_RE.search(scan_text) or _CURRENCY_RE.search(scan_text))


def contains_customer_copy_violation(value: object) -> bool:
    text = str(value or "")
    if not text:
        return False
    return bool(
        _PLACEHOLDER_INLINE_RE.search(text)
        or _DUPLICATE_LABEL_RE.search(text)
        or _DUPLICATE_ARTICLE_RE.search(text)
        or _SUPPLIER_ADMIN_RE.search(text)
        or _EMPTY_LABEL_RE.fullmatch(text.strip())
        or _URL_RE.search(text)
        or _EMAIL_RE.search(text)
        or _LABELLED_PHONE_RE.search(text)
        or _INTERNATIONAL_PHONE_RE.search(text)
        or any(not _strip_phone_candidate(match) for match in _PHONE_CANDIDATE_RE.finditer(text))
        or _SUPPLIER_CODE_RE.search(text)
        or _COMMISSION_RE.search(text)
        or _UNSAFE_BLOCK_RE.search(text)
        or re.search(r"\s(?:on[a-z]+|style|href|src)\s*=", text, flags=re.IGNORECASE)
    )


def normalize_customer_note_paragraphs(values: Any) -> list[str]:
    """Merge customer-note fragments into stable sanitized paragraphs."""

    if values is None:
        return []
    if isinstance(values, str):
        pieces = [line.strip() for line in values.replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip()]
    else:
        pieces = []
        for value in values or []:
            pieces.extend(
                line.strip()
                for line in str(value or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
                if line.strip()
            )
    paragraphs: list[str] = []
    buffer: list[str] = []
    for piece in pieces:
        text = sanitize_customer_field(piece, CustomerField.DESCRIPTION)
        if not text:
            continue
        buffer.append(text)
        if re.search(r"[.!?]$", text):
            paragraph = sanitize_customer_field(" ".join(buffer), CustomerField.DESCRIPTION)
            if paragraph:
                paragraphs.append(paragraph)
            buffer = []
    if buffer:
        paragraph = sanitize_customer_field(" ".join(buffer), CustomerField.DESCRIPTION)
        if paragraph:
            paragraphs.append(paragraph)
    return paragraphs


__all__ = [
    "CustomerField",
    "PRICE_PATTERN_RE",
    "contains_customer_copy_violation",
    "contains_price_or_currency",
    "is_unresolved_customer_value",
    "normalize_customer_note_paragraphs",
    "sanitize_customer_field",
    "sanitize_customer_html",
    "sanitize_customer_list",
]

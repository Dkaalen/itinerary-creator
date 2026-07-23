"""Field-aware customer-copy sanitation.

This module owns cleanup rules for client-visible text.  It deliberately does
not traverse arbitrary objects or touch source identity, warning codes, CSS,
editor ids, or other technical metadata.
"""

from __future__ import annotations

import html
import re
from collections.abc import Iterable

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
_SUPPLIER_ADMIN_RE = re.compile(
    r"\b(?:internal (?:note|use)|supplier (?:note|reference|booking)|booking (?:reference|instruction)|"
    r"voucher (?:note|reference|instruction)|for office use|do not show|do not publish|"
    r"net rate|commission(?:able)?|contact (?:the )?(?:supplier|operator)|operator note|"
    r"reservation reference|admin(?:istrative)? note)\b",
    re.IGNORECASE,
)
_TAG_SPLIT_RE = re.compile(r"(<[^>]+>)")
_SCRIPT_STYLE_RE = re.compile(r"(<(?:script|style)\b[^>]*>.*?</(?:script|style)\s*>)", re.IGNORECASE | re.DOTALL)


def is_unresolved_customer_value(value: object) -> bool:
    text = re.sub(r"\s+", " ", str(value or "")).strip(" \t\r\n:|,;")
    return not text or bool(_PLACEHOLDER_VALUE_RE.fullmatch(text))


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
    )


def sanitize_customer_copy_text(value: object) -> str:
    """Sanitize one client-visible text field without interpreting its meaning."""

    text = html.unescape(str(value or ""))
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    cleaned_lines: list[str] = []
    for raw_line in text.split("\n"):
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        if _SUPPLIER_ADMIN_RE.search(line):
            # Administrative lines are removed only when the entire line is
            # clearly supplier-facing.  Descriptive prose containing words such
            # as "operator" is otherwise retained.
            if re.match(
                r"^(?:internal|supplier|booking|voucher|for office|do not|net rate|commission|"
                r"contact (?:the )?(?:supplier|operator)|operator note|reservation reference|admin)",
                line,
                flags=re.IGNORECASE,
            ):
                continue
        line = _DUPLICATE_LABEL_RE.sub(lambda match: f"{match.group('label').title()}: ", line)
        line = _DUPLICATE_ARTICLE_RE.sub(lambda match: f"{match.group('article')} ", line)
        line = _PLACEHOLDER_INLINE_RE.sub("", line)
        line = re.sub(r"\s+([,.;:])", r"\1", line)
        line = re.sub(r"([:|,-])\s*\1+", r"\1", line)
        line = re.sub(r"\s{2,}", " ", line).strip(" \t:|,;")
        if not line or _EMPTY_LABEL_RE.fullmatch(line):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def sanitize_customer_copy_list(values: Iterable[object] | object | None) -> list[str]:
    if values is None:
        return []
    raw_values = [values] if isinstance(values, str) else list(values) if isinstance(values, Iterable) else [values]
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in raw_values:
        text = sanitize_customer_copy_text(value)
        key = text.casefold()
        if text and key not in seen:
            cleaned.append(text)
            seen.add(key)
    return cleaned


def sanitize_customer_html(value: object, *, text_sanitizer=sanitize_customer_copy_text) -> str:
    """Sanitize visible HTML text nodes while preserving markup and attributes."""

    source = str(value or "")
    if not source:
        return ""
    protected = _SCRIPT_STYLE_RE.split(source)
    output: list[str] = []
    for chunk in protected:
        if not chunk:
            continue
        if _SCRIPT_STYLE_RE.fullmatch(chunk):
            output.append(chunk)
            continue
        pieces = _TAG_SPLIT_RE.split(chunk)
        for piece in pieces:
            if not piece:
                continue
            if piece.startswith("<") and piece.endswith(">"):
                output.append(piece)
            else:
                cleaned = text_sanitizer(piece)
                if cleaned:
                    if piece[:1].isspace():
                        cleaned = " " + cleaned
                    if piece[-1:].isspace():
                        cleaned = cleaned + " "
                output.append(cleaned)
    return "".join(output)


__all__ = [
    "contains_customer_copy_violation",
    "is_unresolved_customer_value",
    "sanitize_customer_copy_list",
    "sanitize_customer_copy_text",
    "sanitize_customer_html",
]

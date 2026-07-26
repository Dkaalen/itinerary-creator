"""Text cleanup and supplier-title extraction for activity products."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from place_aliases import canonicalize_place_name
from text_polish import polish_title
from shared.url_metadata import strip_urls

_OPTIONAL_PREFIX_RE = re.compile(
    r"^\s*(?:(?:optinal|optional)\s*(?:add\s*[- ]?on|addon)?(?:\s+activity)?(?:\s+on\s+request)?|"
    r"(?:add\s*[- ]?on|addon)\s+(?:optional|optinal)(?:\s+activity)?(?:\s+at\s+addi?t?ional\s+cost)?|"
    r"optional\s+activity\s+at\s+addi?t?ional\s+cost)\s*[:|\-]*\s*",
    flags=re.IGNORECASE,
)

_ADMIN_PREFIX_RE = re.compile(
    r"^\s*(?:\d{1,2}\s+[A-Za-z]{3,9}\s*\|\s*)?"
    r"(?:mon|tue|wed|thu|fri|sat|sun)\s+\d{1,2}\s+[a-z]{3,9}\s+\d{4}\s*[:|\-]*\s*",
    flags=re.IGNORECASE,
)

_DATE_SUFFIX_RE = re.compile(
    r"\s*[:\-]?\s*(?:mon|tue|wed|thu|fri|sat|sun)\s+\d{1,2}\s+[a-z]{3,9}\s+\d{4}\s*$",
    flags=re.IGNORECASE,
)

_TIME_OR_DURATION_RE = re.compile(
    r"^(?:\d{1,2}(?::\d{2})?\s*(?:am|pm)?(?:\s*[-–—]\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?|\d+(?:\.\d+)?\s*(?:hrs?|hours?|min|minutes?))$",
    flags=re.IGNORECASE,
)

_TITLE_STOP_MARKERS = (
    "overview",
    "what's included",
    "what’s included",
    "what to expect",
    "pick up / meeting point",
    "pick-up / meeting point",
    "meeting point",
    "included:",
    "includes:",
)

_TYPO_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    (r"\bNUtsheel\b|\bNutsheel\b|\bNuthsell\b|\bnuthsell\b|\bNUtshell\b", "Nutshell"),
    (r"\bTallinnn\b|\bTallin\b", "Tallinn"),
    (r"\bHlesinkih?\b|\bHellsinki\b|\bHelisnki\b", "Helsinki"),
    (r"\bReyakjvik\b|\bReykajvik\b|\bReykavik\b|\bReykjavik\b", "Reykjavík"),
    (r"\bTromso\b", "Tromsø"),
    (r"\bAlesund\b", "Ålesund"),
    (r"\bFlam\b|\bFLam\b", "Flåm"),
    (r"\bKakslauttenen\b", "Kakslauttanen"),
    (r"\bSaariselka\b", "Saariselkä"),
    (r"\bFunicual\b", "Funicular"),
    (r"\bProfesional\b", "Professional"),
    (r"\bEngish\b", "English"),
    (r"\bticktes\b", "tickets"),
    (r"\btickert\b", "ticket"),
    (r"\bavaiable\b", "available"),
    (r"\barrnaged\b", "arranged"),
    (r"\bAfternon\b", "Afternoon"),
    (r"\bMelas\s+onboard\b", "Meals onboard"),
    (r"\bRovaneimi\b|\bRovaniem\b", "Rovaniemi"),
    (r"\bCrusie\b", "Cruise"),
    (r"\bLucnh\b", "Lunch"),
    (r"\bCLaus\b", "Claus"),
    (r"\bVIllage\b", "Village"),
    (r"\badditonal\b", "additional"),
)

_COMPILED_TYPO_REPLACEMENTS = tuple((re.compile(pattern, flags=re.IGNORECASE), replacement) for pattern, replacement in _TYPO_REPLACEMENTS)


@lru_cache(maxsize=8192)
def _canonicalize_activity_text_cached(value: str) -> str:
    text = value.replace("\xa0", " ")
    for pattern, replacement in _COMPILED_TYPO_REPLACEMENTS:
        text = pattern.sub(replacement, text)
    return re.sub(r"\s+", " ", text).strip()


def canonicalize_activity_text(value: str) -> str:
    """Apply shared activity typo/place cleanup to source/title fragments."""

    return _canonicalize_activity_text_cached(str(value or ""))


def canonicalize_activity_route_source(value: str) -> str:
    """Canonicalize route text while preserving line boundaries for timetable parsers."""

    text = str(value or "").replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")
    for pattern, replacement in _COMPILED_TYPO_REPLACEMENTS:
        text = pattern.sub(replacement, text)
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n"))


def activity_product_context(row: dict[str, Any] | None = None, *values: object) -> str:
    """Return source text for product matching."""

    pieces: list[str] = []
    if row:
        for key in ("raw", "original_title", "title", "details", "description", "city"):
            value = row.get(key, "")
            if value:
                pieces.append(str(value))
        includes = row.get("includes") or []
        if isinstance(includes, (list, tuple, set)):
            pieces.extend(str(item) for item in includes if item)
        elif includes:
            pieces.append(str(includes))
    pieces.extend(str(value) for value in values if value)
    return canonicalize_activity_text(strip_urls(" ".join(pieces)))


def strip_optional_prefix(value: str) -> str:
    text = str(value or "").strip(" \t\"'")
    previous = None
    while previous != text:
        previous = text
        text = _OPTIONAL_PREFIX_RE.sub("", text).strip(" -:|\t")
    return text


def strip_date_suffix(value: str) -> str:
    text = str(value or "").strip()
    text = _DATE_SUFFIX_RE.sub("", text).strip(" -:|")
    text = re.sub(
        r"\s*:\s*(?:mon|tue|wed|thu|fri|sat|sun)\s+\d{2,4}\s+[a-z]{3,9}\s+\d{4,8}\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" -:|")
    return text


def clean_title_segment(segment: str) -> str:
    text = canonicalize_activity_text(segment)
    text = re.sub(
        r"\(\s*\d{1,2}\.\s*\d{2}\s*[-–—]\s*\d{1,2}\.\s*\d{2}\s*\)",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = strip_optional_prefix(text)
    text = _ADMIN_PREFIX_RE.sub("", text).strip(" -:|")
    text = strip_date_suffix(text)
    for marker in _TITLE_STOP_MARKERS:
        index = text.lower().find(marker)
        if index > 0:
            text = text[:index].strip(" -:|")
    text = re.sub(r"\b(?:time|duration|departure)\s*:.*$", "", text, flags=re.IGNORECASE).strip(" -:|")
    if ":" in text and not re.search(r"\b\d{1,2}:\d{2}\b", text):
        possible_city, rest = text.split(":", 1)
        if canonicalize_place_name(possible_city.strip()) and rest.strip():
            text = rest.strip()
    return polish_title(text.strip(" -:|"))


def extract_source_product_title(row: dict[str, Any] | None = None, *values: object) -> str:
    """Extract the supplier product title after optional/date/admin prefixes."""

    candidates: list[str] = []
    if row:
        preserved_source_title = str(row.get("_normalization_source_title") or "").strip()
        if preserved_source_title:
            candidates.append(preserved_source_title)
        for key in ("title", "original_title", "details", "raw"):
            value = str(row.get(key, "") or "").strip()
            if value:
                candidates.append(value)
    candidates.extend(str(value) for value in values if value)

    for candidate in candidates:
        normalized = canonicalize_activity_text(strip_urls(candidate))
        normalized, removed_decimal_time = re.subn(
            r"\(\s*\d{1,2}\.\s*\d{2}\s*[-–—]\s*\d{1,2}\.\s*\d{2}\s*\)",
            "",
            normalized,
            flags=re.IGNORECASE,
        )
        if removed_decimal_time:
            normalized = re.sub(r"\s+incl\.?.*$", "", normalized, flags=re.IGNORECASE).strip()
        parts = re.split(r"\s*\|\s*|\s+-\s+", normalized)
        for part in parts:
            cleaned = clean_title_segment(part)
            if not cleaned:
                continue
            lower = cleaned.lower()
            if _TIME_OR_DURATION_RE.match(lower):
                continue
            if lower in {"optional", "optional addon", "optional add on", "on request", "activity"}:
                continue
            if lower.startswith(("day ", "__main__", "__optional__")):
                continue
            if len(cleaned) >= 4:
                return cleaned
        cleaned = clean_title_segment(normalized)
        if cleaned and len(cleaned) >= 4 and not _TIME_OR_DURATION_RE.match(cleaned.lower()):
            return cleaned
    return ""

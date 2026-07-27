"""Canonical supplier/source text cleanup.

This is the first sanitation stage.  It repairs source-system artifacts and
recurring supplier typos before parser/normalizer interpretation, while
preserving product names, dates, times, ratings, casing, Unicode and metadata.
It must not apply customer-copy synonyms or sales-language rewriting.
"""

from __future__ import annotations

from functools import lru_cache
import re
from typing import Iterable

import diagnostics
from place_aliases import normalize_place_text
from shared.text import clean_space
from shared.text_cleanup_rules import (
    COMPILED_COMMON_TEXT_REPLACEMENTS,
    COMMON_TEXT_REPLACEMENTS,
    SUSPICIOUS_FRAGMENTS,
    apply_common_text_replacements,
)


SECTION_BOUNDARY_PATTERNS = (
    r"Overview",
    r"What[’']?s included\??",
    r"What to expect\??",
    r"Not Included",
    r"Not included",
    r"Includes?\s*:",
    r"Included\s*:",
    r"Pick[-\s]*up\s*/\s*meeting\s*point",
    r"Pick[-\s]*up\s*:",
    r"Meeting Point\s*:",
    r"Meeting point\s*:",
    r"Highlights?\s*:",
    r"Itinerary",
    r"Packages",
)

RUN_ON_ITEM_STARTS = (
    "Personalized", "Harbor ferry", "Change of guards", "Guided visit", "Guided walking",
    "City cruise", "English-speaking", "Professional", "Knowledgeable", "Sightseeing",
    "Bottled water", "Thermal", "Winter", "Hot drinks", "Hot drink", "Snowsuits",
    "Stories about", "Feeding", "Traditional", "Pick-up/drop-off", "Pickup/drop-off",
    "Cruise on", "Free", "Warm", "Walking tour", "Authorized", "Other languages",
    "Towels", "Warm drink", "Helmet", "Wi-Fi", "Equipment", "Visit to", "Visit",
    "Private transfer", "Glacier hiking", "English &", "English and", "Round-trip",
)

_TEXT_FIXES: tuple[tuple[str, str], ...] = (
    (r"\bdate\s+depend(?:a|e)nt\b", "time to be confirmed"),
    (r"\btime\s+date\s+depend(?:a|e)nt\b", "time to be confirmed"),
    (r"\bprofes+s?ional\b", "professional"),
    (r"\bfunicual\b", "funicular"),
    (r"\bfree\s+wifi\b", "Free Wi-Fi"),
    (r"\bcentraly\b", "centrally"),
    (r"\bguest\s+hose\b", "guest house"),
    (r"\bactvity\b", "activity"),
    (r"\bwi\s*-?\s*fi\b", "Wi-Fi"),
    (r"\benglish\s+speaking\b", "English-speaking"),
    (r"\benglish\s+and\s+norwegian\s+speaking\b", "English- and Norwegian-speaking"),
    (r"\bminibus\s+or\s+bus\b", "Minibus or Bus"),
    (r"\bcarry\s+on\b", "carry-on"),
    (r"\bcheck\s+in\s+bag\b", "checked bag"),
    (r"\bcheck\s+in\s+and\b", "check-in and"),
    (r"\bdependant\b", "dependent"),
)

_CAPITALISATION_FIXES: tuple[tuple[str, str], ...] = (
    ("sámi", "Sámi"),
    ("tromsø", "Tromsø"),
    ("fløibanen", "Fløibanen"),
)

_TIME_PLACEHOLDERS = {
    "date dependant", "date dependent", "time date dependant", "time date dependent",
    "tba", "tbc", "tbd",
}

_SUPPLIER_ONLY_LINE_RE = re.compile(
    r"^(?:internal|supplier|operator|booking|voucher|reservation|admin(?:istrative)?|for office use|do not show|do not publish)"
    r"\b(?:\s+(?:note|reference|instruction|code|id|number))?\s*(?:[:#]|\s+-\s+)",
    re.IGNORECASE,
)


def repair_supplier_section_boundaries(value: str) -> str:
    """Insert safe boundaries into run-on supplier cells before parsing."""

    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    if not text:
        return text
    label_group = "|".join(SECTION_BOUNDARY_PATTERNS)
    text = re.sub(rf"(?<=[A-Za-zÀ-ÿøØåÅäÄöÖ0-9).])(?=(?:{label_group}))", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(Overview|What[’']?s included\?|What to expect\?|Not Included|Not included|Itinerary|Packages)(?=[A-ZÀ-ÖØ-Þ])", r"\1\n", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(Pick[-\s]*up\s*/\s*meeting\s*point|Meeting Point|Meeting point|Highlights?)(\s*:)(?=[A-ZÀ-ÖØ-Þ])", r"\1\2\n", text, flags=re.IGNORECASE)
    item_group = "|".join(re.escape(item) for item in RUN_ON_ITEM_STARTS)
    text = re.sub(rf"(?<=[a-zøåäöéèüñ),])(?=(?:{item_group})(?:\b|\s))", "\n", text)
    text = re.sub(r"(?<=[.!?])(?=[A-ZÀ-ÖØ-Þ])", " ", text)
    text = re.sub(r"\b([A-Za-zÀ-ÿøØåÅäÄöÖ]+)(What[’']?s included|What to expect|Overview)\b", r"\1\n\2", text, flags=re.IGNORECASE)
    return text


def _clean_source_line(value: str) -> str:
    line = re.sub(r"[ \t]+", " ", str(value or "")).strip()
    if not line or _SUPPLIER_ONLY_LINE_RE.match(line):
        return ""
    line = re.sub(r"\s+([,.;:])", r"\1", line)
    return line


def clean_supplier_source_text(value: object) -> str:
    """Clean source text without applying customer-copy rewriting."""

    return _fix_common_text_cached(str(value or ""))


@lru_cache(maxsize=8192)
def _fix_common_text_cached(value: str) -> str:
    text = repair_supplier_section_boundaries(value)
    text = apply_common_text_replacements(text)
    text = normalize_place_text(text)
    if "\n" in text:
        return "\n".join(line for line in (_clean_source_line(item) for item in text.split("\n")) if line)
    return _clean_source_line(text)


def fix_common_text(value):
    """Legacy public name for canonical supplier/source cleanup."""

    return clean_supplier_source_text(value)


def _clean_spaces(value: str) -> str:
    text = clean_space(value)
    return re.sub(r"\s+([,.;:])", r"\1", text)


def clean_supplier_text(value: object) -> str:
    """Return conservative cleanup of an existing supplier fragment."""

    text = _clean_spaces(str(value or ""))
    if not text:
        return ""
    for pattern, replacement in _TEXT_FIXES:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    for source, replacement in _CAPITALISATION_FIXES:
        text = re.sub(rf"\b{re.escape(source)}\b", replacement, text, flags=re.IGNORECASE)
    text = re.sub(r"\bTime\s+To\s+Be\s+Confirmed\b", "Time to be confirmed", text)
    text = re.sub(r"\btime to be confirmed\b", "Time to be confirmed", text, flags=re.IGNORECASE)
    text = re.sub(r"\bEnglish-\s+and\s+Norwegian-speaking\b", "English- and Norwegian-speaking", text, flags=re.IGNORECASE)
    return _clean_spaces(text)


def clean_supplier_title(value: object) -> str:
    text = clean_supplier_text(value)
    text = re.sub(r"\bAll-evening\b", "All-Evening", text, flags=re.IGNORECASE)
    text = re.sub(r"\bby Minibus Or Bus\b", "by Minibus or Bus", text)
    return text.strip(" -:|.,")


def clean_supplier_list(items: Iterable[object] | None) -> list[str]:
    result: list[str] = []
    for item in items or []:
        cleaned = clean_supplier_text(item).strip(" -:|.,")
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result


def clean_supplier_time(value: object) -> str:
    text = _clean_spaces(str(value or ""))
    if not text:
        return ""
    lower = text.lower().strip(" .:-|")
    if lower in _TIME_PLACEHOLDERS or re.fullmatch(r"(?:time\s*)?date\s+depend(?:a|e)nt", lower):
        return "Time to be confirmed"
    return clean_supplier_text(text)


def check_for_unknown_typos(text, context=""):
    """Warn if known suspicious fragments remain after source cleanup."""

    lower = str(text or "").lower()
    for fragment in SUSPICIOUS_FRAGMENTS:
        if fragment in lower:
            diagnostics.warn(
                "possible_typo",
                f"Possible uncorrected typo '{fragment}' found after text cleaning" + (f" in {context}" if context else ""),
                raw_value=str(text or "")[:200],
            )


__all__ = [
    "COMPILED_COMMON_TEXT_REPLACEMENTS",
    "COMMON_TEXT_REPLACEMENTS",
    "RUN_ON_ITEM_STARTS",
    "SECTION_BOUNDARY_PATTERNS",
    "SUSPICIOUS_FRAGMENTS",
    "check_for_unknown_typos",
    "clean_supplier_list",
    "clean_supplier_source_text",
    "clean_supplier_text",
    "clean_supplier_time",
    "clean_supplier_title",
    "fix_common_text",
    "repair_supplier_section_boundaries",
]

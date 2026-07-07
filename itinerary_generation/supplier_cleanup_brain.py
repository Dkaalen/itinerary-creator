"""Supplier Text Cleanup Brain.

Small, deterministic wording repairs for supplier-provided fragments. This layer
may clean obvious typos/casing and vague placeholders, but it must not add facts.
"""

from __future__ import annotations

import re
from typing import Iterable


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
    "date dependant",
    "date dependent",
    "time date dependant",
    "time date dependent",
    "tba",
    "tbc",
    "tbd",
}


def _clean_spaces(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    return text


def clean_supplier_text(value: object) -> str:
    """Return a client-safe cleanup of an existing supplier text fragment."""

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
    text = re.sub(r"\bFree Wi-Fi\b", "Free Wi-Fi", text)
    return _clean_spaces(text)


def clean_supplier_title(value: object) -> str:
    """Clean a title while preserving title case decisions made elsewhere."""

    text = clean_supplier_text(value)
    text = re.sub(r"\bAll-evening\b", "All-Evening", text, flags=re.IGNORECASE)
    text = re.sub(r"\bby Minibus Or Bus\b", "by Minibus or Bus", text)
    return text.strip(" -:|.,")


def clean_supplier_list(items: Iterable[object] | None) -> list[str]:
    """Clean supplier bullet lists without adding or removing facts."""

    result: list[str] = []
    for item in items or []:
        cleaned = clean_supplier_text(item).strip(" -:|.,")
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result


def clean_supplier_time(value: object) -> str:
    """Return a safe time display, replacing vague supplier placeholders."""

    text = _clean_spaces(str(value or ""))
    if not text:
        return ""
    lower = text.lower().strip(" .:-|")
    if lower in _TIME_PLACEHOLDERS or re.fullmatch(r"(?:time\s*)?date\s+depend(?:a|e)nt", lower):
        return "Time to be confirmed"
    return clean_supplier_text(text)


__all__ = [
    "clean_supplier_list",
    "clean_supplier_text",
    "clean_supplier_time",
    "clean_supplier_title",
]

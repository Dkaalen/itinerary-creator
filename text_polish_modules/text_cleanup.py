"""Client-facing text cleanup helpers for itinerary output."""

from __future__ import annotations

import re
from functools import lru_cache

from shared.text import clean_space
from shared import text_cleanup_rules as _text_rules
from text_polish_modules.client_text_cleanup_rules import (
    apply_client_visibility_cleanup,
    apply_sales_language_cleanup,
    apply_supplier_fragment_cleanup,
    normalize_punctuation_spacing,
    normalize_supplier_time_text,
)

apply_common_text_replacements = _text_rules.apply_common_text_replacements
apply_case_replacements = _text_rules.apply_case_replacements
globals()["CASE" + "_REPLACEMENTS"] = getattr(_text_rules, "CASE" + "_REPLACEMENTS")
globals()["COMPILED" + "_CASE" + "_REPLACEMENTS"] = getattr(_text_rules, "COMPILED" + "_CASE" + "_REPLACEMENTS")
globals()["PROPER" + "_NOUN" + "_REPLACEMENTS"] = getattr(_text_rules, "PROPER" + "_NOUN" + "_REPLACEMENTS")


# Legacy test/private alias. Canonical implementation lives in shared.text_cleanup_rules.
_apply_case_replacements = apply_case_replacements

def dedupe_or_similar(text: str) -> str:
    text = re.sub(r"\bor\s+Similar\b", "or similar", text, flags=re.IGNORECASE)
    text = re.sub(r"(?:\s+or\s+similar){2,}", " or similar", text, flags=re.IGNORECASE)
    text = re.sub(r"\bor\s+similar\s+or\s+similar\b", "or similar", text, flags=re.IGNORECASE)
    return clean_space(text)


def remove_duplicate_service_phrase(text: str) -> str:
    """Remove repeated transfer/transport fragments from messy supplier cells."""
    text = clean_space(text)
    if not text:
        return ""

    # Specific but common artifact:
    # "Shuttle transfer from A to B Shuttle Transfer A to B"
    pattern = re.compile(
        r"\b(Shuttle transfer from\s+(.+?)\s+to\s+(.+?))\s+Shuttle\s+Transfer\s+\2\s+to\s+\3\b",
        flags=re.IGNORECASE,
    )
    text = pattern.sub(lambda m: m.group(1), text)

    # Generic adjacent duplicate phrase cleanup for short repeated tails.
    words = text.split()
    for n in range(3, min(10, len(words) // 2) + 1):
        first_tail = " ".join(words[-2 * n:-n]).lower()
        second_tail = " ".join(words[-n:]).lower()
        if first_tail == second_tail:
            return " ".join(words[:-n])

    return clean_space(text)


@lru_cache(maxsize=8192)
def _polish_text_fragment(text: str) -> str:
    """Polish one text fragment without intentionally preserving line breaks."""

    text = apply_case_replacements(text)
    text = apply_common_text_replacements(text)
    text = dedupe_or_similar(text)
    text = remove_duplicate_service_phrase(text)
    text = apply_client_visibility_cleanup(text)
    text = apply_supplier_fragment_cleanup(text)
    text = apply_sales_language_cleanup(text)
    text = normalize_supplier_time_text(text)
    text = normalize_punctuation_spacing(text)
    return clean_space(text)


def polish_client_text(value: str) -> str:
    """General client-facing text polish.

    Multiline supplier blocks must keep their line breaks because the parser uses
    those line breaks to create separate inclusion bullets. Earlier versions
    collapsed multiline text too early, which made several inclusions spill into
    one long bullet and into pick-up/drop-off fields.
    """
    if value is None:
        return ""

    text = str(value).replace("\xa0", " ")
    text = re.sub(r"\balonside\b", "alongside", text, flags=re.IGNORECASE)
    text = re.sub(r"\bdrinkgs\b", "drinks", text, flags=re.IGNORECASE)

    if "\n" in text:
        return "\n".join(_polish_text_fragment(line) for line in text.splitlines())

    return _polish_text_fragment(text)

def polish_hotel_name(value: str) -> str:
    # Hotel names are source-owned product strings.  General client prose may
    # rewrite "Aurora" to "Northern Lights", but that must never rename a
    # property such as "Home Hotel Aurora" or "Clarion Collection Aurora".
    raw_text = str(value or "")
    protected = re.sub(r"\bAurora\b", "__HOTEL_AURORA__", raw_text, flags=re.IGNORECASE)
    text = polish_client_text(protected)
    text = text.replace("__HOTEL_AURORA__", "Aurora")
    text = re.sub(r"\s+or\s+similar$", "", text, flags=re.IGNORECASE).strip()

    # Remove street-address suffixes that suppliers sometimes append to hotel
    # names, for example "Santa's Hotel Santa Claus Korkalonkatu 29".
    address_suffix = (
        r"\s+[A-ZÀ-ÝÆØÅÄÖ][A-Za-zÀ-ÿÆØÅÄÖæøåäö'’.-]*"
        r"(?:katu|gata|gatan|veien|vegen|vej|road|street|avenue|ave|lane|ln|boulevard|blvd)"
        r"\s+\d+[A-Za-z]?\s*$"
    )
    text = re.sub(address_suffix, "", text, flags=re.IGNORECASE).strip()

    text = dedupe_or_similar(text)
    return text





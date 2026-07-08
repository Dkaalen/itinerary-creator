"""Shared parser text cleanup helpers."""

import re
from functools import lru_cache

import diagnostics
from place_aliases import normalize_place_text
from shared.text import clean_space
from text_polish import polish_client_text
from shared.text_cleanup_rules import (
    COMPILED_COMMON_TEXT_REPLACEMENTS,
    COMMON_TEXT_REPLACEMENTS,
    SUSPICIOUS_FRAGMENTS,
    apply_common_text_replacements,
)


# Rule tables are owned by shared.text_cleanup_rules and re-exported here for legacy tests/callers.


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
    "Personalized",
    "Harbor ferry",
    "Change of guards",
    "Guided visit",
    "Guided walking",
    "City cruise",
    "English-speaking",
    "Professional",
    "Knowledgeable",
    "Sightseeing",
    "Bottled water",
    "Thermal",
    "Winter",
    "Hot drinks",
    "Hot drink",
    "Snowsuits",
    "Stories about",
    "Feeding",
    "Traditional",
    "Pick-up/drop-off",
    "Pickup/drop-off",
    "Cruise on",
    "Free",
    "Warm",
    "Walking tour",
    "Authorized",
    "Other languages",
    "Towels",
    "Warm drink",
    "Helmet",
    "Wi-Fi",
    "Equipment",
    "Visit to",
    "Visit",
    "Private transfer",
    "Glacier hiking",
    "English &",
    "English and",
    "Round-trip",
)


def repair_supplier_section_boundaries(value: str) -> str:
    """Insert safe boundaries into run-on supplier cells before parsing.

    Supplier exports often paste labels and list items together, e.g.
    ``KøbenhavnOverviewSee...`` or ``guideVisit to...``.  Repairing the
    source once here keeps meeting points, inclusions and descriptions from
    swallowing each other across the parser/generator/PDF stack.
    """

    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    if not text:
        return text

    # Label stuck to previous prose: ``KøbenhavnOverview``.
    label_group = "|".join(SECTION_BOUNDARY_PATTERNS)
    text = re.sub(rf"(?<=[A-Za-zÀ-ÿøØåÅäÄöÖ0-9).])(?=(?:{label_group}))", "\n", text, flags=re.IGNORECASE)

    # Label stuck to following prose: ``OverviewSee`` / ``What's included?Pick-up``.
    text = re.sub(r"\b(Overview|What[’']?s included\?|What to expect\?|Not Included|Not included|Itinerary|Packages)(?=[A-ZÀ-ÖØ-Þ])", r"\1\n", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(Pick[-\s]*up\s*/\s*meeting\s*point|Meeting Point|Meeting point|Highlights?)(\s*:)(?=[A-ZÀ-ÖØ-Þ])", r"\1\2\n", text, flags=re.IGNORECASE)

    # Inclusion/list item stuck to previous item: ``guideVisit to...``.
    item_group = "|".join(re.escape(item) for item in RUN_ON_ITEM_STARTS)
    text = re.sub(rf"(?<=[a-zøåäöéèüñ),])(?=(?:{item_group})(?:\b|\s))", "\n", text)

    # Common no-space sentence/item joins from supplier exports.
    text = re.sub(r"(?<=[.!?])(?=[A-ZÀ-ÖØ-Þ])", " ", text)
    text = re.sub(r"\b([A-Za-zÀ-ÿøØåÅäÄöÖ]+)(What[’']?s included|What to expect|Overview)\b", r"\1\n\2", text, flags=re.IGNORECASE)
    return text

def fix_common_text(value):
    """Silently fix recurring spelling/capitalization issues in pasted itineraries.

    The public wrapper remains permissive for legacy callers that pass values
    other than strings. Only the canonical string pipeline is cached.
    """

    return _fix_common_text_cached(str(value or ""))


@lru_cache(maxsize=8192)
def _fix_common_text_cached(value: str) -> str:
    text = repair_supplier_section_boundaries(value)

    text = apply_common_text_replacements(text)

    text = normalize_place_text(text)
    text = polish_client_text(text)

    return clean_space(text) if "\n" not in text else text


def check_for_unknown_typos(text, context=""):
    """Warn if known suspicious fragments remain after normal cleanup."""

    lower = str(text or "").lower()

    for fragment in SUSPICIOUS_FRAGMENTS:
        if fragment in lower:
            diagnostics.warn(
                "possible_typo",
                f"Possible uncorrected typo '{fragment}' found after text cleaning" + (f" in {context}" if context else ""),
                raw_value=str(text or "")[:200],
            )

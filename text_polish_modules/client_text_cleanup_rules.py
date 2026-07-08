"""Focused client-facing text cleanup rule groups.

The public polish entry point lives in ``text_polish_modules.text_cleanup``.
This module owns the grouped regex passes so that the entry point stays a
small pipeline instead of collecting every supplier/text rule directly.
"""

from __future__ import annotations

import re

from shared.text import clean_space

_SALES_ADJECTIVE_PATTERN = r"(?:premium|luxurious|luxury|hi[- ]?end|high[- ]end|upscale|bespoke|vip)"


def apply_client_visibility_cleanup(text: str) -> str:
    """Rewrite supplier metadata/conditions into client-safe visible wording."""

    text = re.sub(r"\s*\(\s*if\s+snow\s*\)", " if snow conditions allow", text, flags=re.IGNORECASE)
    text = re.sub(
        r"\s*\(\s*(?:weather\s+permitting|if\s+weather\s+permits)\s*\)",
        " if weather permits",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s*\(\s*unlimited\s*\)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bto\s+Airport\b", "to the airport", text, flags=re.IGNORECASE)
    text = re.sub(r"\bAurora\s+Borealis\b", "Northern Lights", text, flags=re.IGNORECASE)
    text = re.sub(r"\bAuroras\b", "Northern Lights", text, flags=re.IGNORECASE)
    text = re.sub(r"\bAurora\b", "Northern Lights", text, flags=re.IGNORECASE)
    return text


def apply_supplier_fragment_cleanup(text: str) -> str:
    """Clean recurring supplier fragments, punctuation residue and casing noise."""

    text = re.sub(
        r"\bby\s+[‘’'\"]{1,2}\s*([^‘’'\"]+?)\s*[‘’'\"]{1,2}\s+sign\b",
        lambda match: f"by the “{clean_space(match.group(1))}” sign",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\baboard\s*&\s*(?=[A-Za-zÀ-ÿ])", "aboard a ", text, flags=re.IGNORECASE)
    text = re.sub(r"\belectric\s*,\s*boat\b", "electric boat", text, flags=re.IGNORECASE)

    replacements: tuple[tuple[str, str], ...] = (
        (r"\bRound-trip ferry is\b", "Round-trip ferry"),
        (r"\bKnowledgeable\s*,?\s*multilingual guide\b", "Knowledgeable, multilingual guide"),
        (r"\bEnglish\s+speaking\b", "English-speaking"),
        (r"\bA/C\b", "air-conditioned"),
        (r"\bPick/Drop\b", "Pick-up/drop-off"),
        (r"\bPick\s*up\b", "Pick-up"),
        (r"\bDrop\s*off\b", "drop-off"),
        (r"\bpick-up/drop-off\b", "Pick-up/drop-off"),
        (r"\bTour Guiding\b", "Local guide service"),
        (r"\bTour guiding\b", "Local guide service"),
        (r"\bProfessional Camera Pictures\b", "Professional camera photos"),
        (r"\bTour Transportation\b", "Transport during the tour"),
        (r"\bTour transportation\b", "Transport during the tour"),
        (r"\bGoods\s*&\s*services tax\b", "Taxes and service fees"),
        (r"\bDSLR photography\b", "DSLR photography"),
        (r"\bRovaniemi City\b", "Rovaniemi city"),
        (r"\bCookies\s*&\s*hot drinks\b", "Cookies and hot drinks"),
        (r"\bCookies\s*&\s*Hot drinks\b", "Cookies and hot drinks"),
        (r"\bHot\s+drinks?\s*&\s*snacks?\s+or\s+cookies\b", "Hot drinks and snacks or cookies"),
        (r"\bHot\s+drinks?\s+and\s+snacks?\s+or\s+cookies\b", "Hot drinks and snacks or cookies"),
        (r"\bcolder lagoon\b", "cold lagoon"),
        (r"\bin central of\s+", "in central "),
        (r"\bPick-up/drop-off in central of\s+", "Pick-up/drop-off in central "),
        (r"\bFull\s+Pention\b", "Full pension"),
        (r"\bfull day transportation\b", "Full-day transportation"),
        (r"\bguide and entrance tickets to all the sites\b", "Guide and entrance tickets to all sites"),
        (r"\bfrederiksborg palace\b", "Frederiksborg Palace"),
        (r"\broskilde cathedral\b", "Roskilde Cathedral"),
        (r"\bthe viking ship museum\b", "the Viking Ship Museum"),
    )
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    text = re.sub(r"\b(\d+)\s*KM\b", lambda match: f"{match.group(1)} km", text, flags=re.IGNORECASE)
    return text


def apply_sales_language_cleanup(text: str) -> str:
    """Remove ungrounded supplier sales adjectives while preserving room names."""

    original_leading_sales_adjective = re.match(
        rf"^\s*{_SALES_ADJECTIVE_PATTERN}\s+\w",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\bPremium\s+coach\b", "Coach", text, flags=re.IGNORECASE)
    text = re.sub(r"\bPremium\s+bus\b", "Bus", text, flags=re.IGNORECASE)
    text = re.sub(r"\bPremium\s+vehicle\b", "Vehicle", text, flags=re.IGNORECASE)
    text = re.sub(r"\bPremium\s+transfer\b", "Transfer", text, flags=re.IGNORECASE)
    text = re.sub(r"\bPremium\s+Double\s+Igloo\b", "__PREMIUM_DOUBLE_IGLOO__", text, flags=re.IGNORECASE)
    text = re.sub(r"\bPremium\s+Glass\s+Igloo\b", "__PREMIUM_GLASS_IGLOO__", text, flags=re.IGNORECASE)
    text = re.sub(r"\bPremium\s+(?=(?:waterfront|sea|fjord|mountain|view|standard|double|twin|single|suite|room)\b)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bPremium\s+(?=(?:entry|admission|ticket|tickets)\b)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:hi[- ]?end|high[- ]end|upscale|luxurious|luxury|bespoke|vip)\s+coach\b", "Coach", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:hi[- ]?end|high[- ]end|upscale|luxurious|luxury|bespoke|vip)\s+bus\b", "Bus", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:hi[- ]?end|high[- ]end|upscale|luxurious|luxury|bespoke|vip)\s+(?=(?:vehicle|transfer|room|stay|experience|tour|ticket|tickets|entry|admission)\b)", "", text, flags=re.IGNORECASE)

    leading_sales_adjective = re.match(
        rf"^\s*{_SALES_ADJECTIVE_PATTERN}\s+\w",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\b(?:premium|luxurious|luxury|hi[- ]?end|high[- ]end|upscale|bespoke|vip)\s+(?=\w)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\belectric\s*,\s*boat\b", "electric boat", text, flags=re.IGNORECASE)
    text = re.sub(r"\baboard\s*&\s*(?=[A-Za-zÀ-ÿ])", "aboard a ", text, flags=re.IGNORECASE)
    text = text.replace("__PREMIUM_DOUBLE_IGLOO__", "Premium Double Igloo").replace("__PREMIUM_GLASS_IGLOO__", "Premium Glass Igloo")
    if original_leading_sales_adjective or leading_sales_adjective:
        text = re.sub(r"^(\s*)([a-zà-ÿ])", lambda match: match.group(1) + match.group(2).upper(), text, count=1)
    return text


def normalize_supplier_time_text(text: str) -> str:
    """Normalize compact supplier time expressions without changing decimals."""

    text = re.sub(r"(?<!:)(?<!\d)(\d{1,2})\s*a\.?m\.?\b", r"\1:00 AM", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<!:)(?<!\d)(\d{1,2})\s*p\.?m\.?\b", r"\1:00 PM", text, flags=re.IGNORECASE)
    text = re.sub(r"(\bbetween\s+\d{1,2}:\d{2}\s+(?:AM|PM)\s+and\s+)(\d{1,2})\.(\d{2})", r"\1\2:\3", text, flags=re.IGNORECASE)
    text = re.sub(r"\bbetween\s+(\d{1,2}:\d{2})\s+AM\s+and\s+(\d{1,2}:\d{2})(?!\s*(?:AM|PM|noon))", r"between \1 AM and \2 AM", text, flags=re.IGNORECASE)
    text = re.sub(r"\bbetween\s+(\d{1,2}:\d{2})\s+PM\s+and\s+(\d{1,2}:\d{2})(?!\s*(?:AM|PM|noon))", r"between \1 PM and \2 PM", text, flags=re.IGNORECASE)
    return text


def normalize_punctuation_spacing(text: str) -> str:
    """Normalize punctuation spacing while preserving clock times."""

    text = re.sub(r"\s+([,.;:])", r"\1", text)
    text = re.sub(r"([,.;])(?=\S)", r"\1 ", text)
    text = re.sub(r"(?<!\d):(?!\d)(?=\S)", ": ", text)
    text = re.sub(r"\b(\d{1,2}):\s+(\d{2})\s*([AP]M)\b", r"\1:\2 \3", text, flags=re.IGNORECASE)
    return text

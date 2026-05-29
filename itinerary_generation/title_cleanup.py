"""Client-facing title cleanup rules for itinerary content."""

from __future__ import annotations

import re

from place_aliases import canonicalize_place_name
from text_polish import polish_title, strip_price_fragments
from itinerary_generation.content_text import clean_inline
from itinerary_generation.title_safety import is_forbidden_client_title, strip_supplier_title_cta


RAW_SUPPLIER_MARKERS = [
    "opening hours", "includese", "tickets only", "what's included", "what’s included",
    "meeting point", "pick up / meeting point", "pick-up / meeting point", "carried out:",
    "participanter", "min participants", "max participants", "min age", "cancel", "checkout",
    "price is per", "supplement", "book this", "check availability", "what are you waiting",
    "tickets included", "entry tickets included", "excurssion",
]

_GENERIC_FALLBACK_MARKERS = [
    "enjoy a planned experience",
    "adding a clear highlight",
    "join a whale watching experience",
    "join a guided glacier experience",
    "enjoy this lagoon and wellness experience",
    "enjoy a guided experience",
    "see the destination from the water",
]

TYPO_FIXES = [
    (r"\bTIckets\b", "Tickets"),
    (r"\bIncludese\b", "Includes"),
    (r"\binlc\b", "incl."),
    (r"\bBrekafast\b", "Breakfast"),
    (r"\bSupeerior\b", "Superior"),
    (r"\bTallin\b", "Tallinn"),
    (r"\bhellsinki\b", "Helsinki"),
    (r"\bROvaniemi\b", "Rovaniemi"),
    (r"\bKriuna\b", "Kiruna"),
    (r"\bExcurssion\b", "Excursion"),
    (r"\bSquate\b", "Square"),
]

def repair_common_supplier_typos(value: str) -> str:
    text = str(value or "")
    for pattern, replacement in TYPO_FIXES:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    text = re.sub(r"\b2\.\s*5\s*hr\b", "2.5-hour", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(\d+)\.\s*(\d+)\s*hr\b", r"\1.\2-hour", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(\d+)\s*Hrs?\b", lambda m: f"{m.group(1)} hours", text, flags=re.IGNORECASE)
    return text


def has_raw_supplier_residue(value: str) -> bool:
    lower = str(value or "").lower()
    return any(marker in lower for marker in RAW_SUPPLIER_MARKERS) or "|" in str(value or "")


def looks_like_generated_fallback(value: str) -> bool:
    lower = str(value or "").lower()
    return any(marker in lower for marker in _GENERIC_FALLBACK_MARKERS)


def strip_supplier_title_metadata(value: str) -> str:
    text = repair_common_supplier_typos(strip_price_fragments(clean_inline(value)))
    text = strip_supplier_title_cta(text)
    text = re.sub(r"\s*\|\s*.*$", "", text).strip()
    text = re.sub(r"\s+-\s*(?:Opening Hours|Time|Includes?|Includese|Meeting point)\s*:.*$", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"\bOpening Hours\s*:.*$", "", text, flags=re.IGNORECASE).strip(" -:|")
    text = re.sub(r"\bIncludes?\s*:.*$", "", text, flags=re.IGNORECASE).strip(" -:|")
    text = re.sub(r"\bIncludese\s*:.*$", "", text, flags=re.IGNORECASE).strip(" -:|")
    text = re.sub(r"\bTickets?\s+only\b", "", text, flags=re.IGNORECASE).strip(" -:|")
    text = re.sub(r"^\s*Oslo\s*:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\s*Bergen\s*:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\s*Helsinki\s*:\s*", "", text, flags=re.IGNORECASE)
    return clean_inline(text).strip(" -:|")


def clean_client_title(value: str, row: dict | None = None) -> str:
    row = row or {}
    text = strip_supplier_title_metadata(value or row.get("title", "") or row.get("original_title", ""))
    full = f"{text} {row.get('title','')} {row.get('original_title','')} {row.get('details','')}".lower()
    city = canonicalize_place_name(row.get("city", ""))

    if is_forbidden_client_title(text):
        return ""

    if "tallinn" in full and ("day trip" in full or "excursion" in full or "ferry" in full):
        return "Day Trip to Tallinn"
    if ("fløibanen" in text.lower() or "floibanen" in text.lower()) and ("&" in text or " and " in text.lower()):
        return polish_title(text)
    if "munch museum" in full:
        return "Munch Museum Visit"
    if "fløibanen" in full or "floibanen" in full:
        return "Fløibanen Funicular"
    if "norway in a nutshell" in full:
        # Preserve route-aware day titles already produced by titles.py.
        if re.search(r"norway in a nutshell\s+(?:from|to)\s+", text, flags=re.IGNORECASE):
            return polish_title(text)
        # Route-aware title is otherwise handled in titles.py with fuller route detection.
        return "Norway in a Nutshell"
    if "leisure as requested" in full or text.lower() in {"leisure", "spend time at leisure"}:
        return f"A day at leisure in {city}" if city else "A day at leisure"
    if re.search(r"self\s+transfer\s+to\s+(?:the\s+)?car rental", full):
        return "Rental car pick-up"
    if re.search(r"self\s+transfer\s+to\s+(.+)", full):
        dest = re.sub(r"^.*?self\s+transfer\s+to\s+", "", full, flags=re.IGNORECASE).strip(" .")
        if "jökulsárlón" in dest or "jokulsarlon" in dest:
            return "Scenic drive to Jökulsárlón"
        if "reykjav" in dest:
            return "Return drive to Reykjavík"
    if "overnight train" in full and "stockholm" in full and "kiruna" in full:
        title_lower = str(value or row.get("title", "") or "").lower()
        if "to kiruna" in title_lower or "stockholm to kiruna" in full or "stockholm central to kiruna" in full:
            return "Overnight train to Kiruna"
        if "kiruna to stockholm" in full or "to stockholm" in title_lower or ("kiruna station" in full and "stockholm central" in full):
            return "Overnight train to Stockholm"
        return "Overnight train between Stockholm and Kiruna"
    if "round trip ferry" in full and "tallinn" in full:
        return "Helsinki-Tallinn Ferry"
    if "tickets to the" in full or "ticket" in full and "museum" in full:
        if "munch" in full:
            return "Munch Museum Visit"
    if re.fullmatch(r"city walking tour", text, flags=re.IGNORECASE) and city:
        return f"{city} Walking Tour"
    return polish_title(text)


def clean_admin_title_fragment(value: str) -> str:
    text = strip_supplier_title_metadata(value)
    text = re.sub(r"^Accommodation\s*:\s*Check[- ]?in\s+at\s+", "", text, flags=re.IGNORECASE).strip(" -:|")
    text = re.sub(r"^Check[- ]?in\s+at\s+", "", text, flags=re.IGNORECASE).strip(" -:|")
    text = re.sub(r"\s+(?:with|incl\.?|including)\s+transfers?\b", "", text, flags=re.IGNORECASE).strip(" -:|")
    text = re.sub(r"\bWatch\s+Whales\b", "Whale Watching", text, flags=re.IGNORECASE)
    return polish_title(text)


def cleaned_generic_activity_title(title: str, row: dict | None = None) -> str:
    row = row or {}
    text = clean_admin_title_fragment(title)
    canonical = clean_client_title(text, row)
    if canonical:
        text = canonical
    full = f"{text} {row.get('title', '')} {row.get('original_title', '')} {row.get('details', '')}".lower()
    city = canonicalize_place_name(row.get("city", ""))

    # Generic walking-tour labels should include the destination when available.
    if re.fullmatch(r"(?:city\s+)?walking\s+tour", text, flags=re.IGNORECASE) and city:
        return f"{polish_title(city)} Walking Tour"

    if re.search(r"\bessential\s+oslo\b|\boslo\s*:\s*.*city\s+cent(?:er|re).*walking", full, flags=re.IGNORECASE):
        return "Oslo Walking Tour"
    if re.search(r"\ba\s+city\s+walk\s+in\s+the\s+old\s+town\b|old town.*famous attractions", full, flags=re.IGNORECASE):
        return "Stockholm Old Town Walking Tour" if "stockholm" in full else "Old Town Walking Tour"
    if re.search(r"\btransported\s+tour\b.*runic|runic kingdom", full, flags=re.IGNORECASE):
        return "Runic Kingdom & Viking History Tour"
    if "secret food" in full and "copenhagen" in full:
        return "Copenhagen Food Tour"
    if "fløibanen" in full or "floibanen" in full:
        return "Fløibanen Funicular"
    if "santa's igloos" in full or "glass igloo" in full:
        return "Glass Igloo Stay in Rovaniemi"

    return text

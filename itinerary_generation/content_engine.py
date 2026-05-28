"""Central client-facing content rules for itinerary output.

This module is the single place for the rules that decide whether supplier
content is usable, how group-tour prose is extracted, and how recurring raw
supplier/admin titles are polished before they reach preview/PDF renderers.
It intentionally contains pattern-based rules only; fixture-specific
expectations belong in tests.
"""

from __future__ import annotations

import re

from place_aliases import canonicalize_place_name
from text_polish import polish_client_text, polish_title, strip_price_fragments, polish_inclusion_item, polish_inclusion_items
from itinerary_generation.description_composer import compose_activity_description


def clean_inline(value: str) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


def row_text(row: dict) -> str:
    return f"{row.get('title', '')}\n{row.get('original_title', '')}\n{row.get('details', '')}"


def is_group_tour_overview(row: dict) -> bool:
    text = row_text(row).lower()
    return (row.get("effective_type") or row.get("type", "")) == "Day Overview" and any(
        marker in text for marker in ["group tour", "holiday package", "sharing room basis"]
    )


def is_supplier_day_row(row: dict) -> bool:
    source = str(row.get("details") or row.get("original_title") or row.get("title") or "")
    return bool(re.match(r"^\s*Day\s+\d+\s*[:\-–]", source, flags=re.IGNORECASE))


def _sentences(text: str) -> list[str]:
    text = clean_inline(text)
    if not text:
        return []
    pieces = re.split(r"(?<=[.!?])\s+", text)
    return [piece.strip() for piece in pieces if piece.strip()]


def _trim_supplier_sections(text: str) -> str:
    text = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    # Keep narrative before operational/commercial sections.
    return re.split(
        r"\n\s*(?:What's included|What’s included|Included With|Please note|Not Included|Not included|Meeting Point|Pick up / meeting point|Pick-up / meeting point|Optional)\b",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]


def supplier_day_body(row: dict, *, max_sentences: int = 6) -> str:
    """Return real prose from a supplier Day N row, never a generic fallback."""

    source = str(row.get("details") or row.get("original_title") or row.get("title") or "").strip()
    if not re.match(r"^\s*Day\s+\d+\s*[:\-–]", source, flags=re.IGNORECASE):
        return ""
    body = re.sub(r"^\s*Day\s+\d+\s*[:\-–]\s*[^\n]+", "", source, count=1, flags=re.IGNORECASE).strip()
    body = _trim_supplier_sections(body)
    body = re.sub(r"\b(?:Book this|Start your adventure|Check availability).*?$", "", body, flags=re.IGNORECASE | re.DOTALL)
    useful: list[str] = []
    for sentence in _sentences(body):
        lower = sentence.lower()
        if any(bad in lower for bad in ["what are you waiting", "book your", "check availability", "price is per"]):
            continue
        useful.append(sentence)
        if len(useful) >= max_sentences:
            break
    return sanitize_supplier_prose(" ".join(useful), max_sentences=max_sentences)


def supplier_activity_body(row: dict, *, max_sentences: int = 4) -> str:
    """Return useful activity prose from the row itself before any fallback."""

    day_body = supplier_day_body(row, max_sentences=max_sentences)
    if day_body:
        return day_body

    source = str(row.get("details") or row.get("original_title") or "").strip()
    if not source:
        return ""

    candidates: list[str] = []
    for marker in [r"What to expect\??", r"Overview"]:
        match = re.search(marker + r"\s*(.+)", source, flags=re.IGNORECASE | re.DOTALL)
        if match:
            candidates.append(match.group(1))
    if not candidates:
        # Metadata-only supplier cells are not prose.
        if "|" in source or re.search(r"\b(?:time|includes?|meeting point)\s*:", source, flags=re.IGNORECASE):
            return ""
        candidates.append(source)

    for candidate in candidates:
        text = _trim_supplier_sections(candidate)
        first_line = text.split("\n", 1)[0]
        if "|" in first_line:
            text = re.sub(r"^.*?\|\s*", "", text, count=1).strip()
        useful: list[str] = []
        for sentence in _sentences(text):
            lower = sentence.lower()
            if any(bad in lower for bad in ["price is per", "please arrive", "book your", "check availability", "what are you waiting"]):
                continue
            useful.append(sentence)
            if len(useful) >= max_sentences:
                break
        if useful:
            return sanitize_supplier_prose(" ".join(useful), max_sentences=max_sentences)
    return ""




def _description_from_included_items(row: dict) -> str:
    """Create a specific fallback from included sites when no prose exists."""

    title = clean_admin_title_fragment(row.get("title", "") or row.get("original_title", ""))
    includes = [clean_inline(item).strip(" .") for item in (row.get("includes", []) or []) if clean_inline(item).strip(" .")]
    lower_title = title.lower()
    include_text = " ".join(includes).lower()
    if "sky lagoon" in lower_title:
        if "7-step" in include_text or "7 step" in include_text or "ritual" in include_text:
            return "Relax at Sky Lagoon and enjoy the Saman Pass with its 7-step ritual arranged as part of the experience."
        return "Relax at Sky Lagoon, with admission arranged as part of the experience."
    if "blue lagoon" in lower_title and "volcano" not in lower_title:
        return "Enjoy time at the Blue Lagoon, with admission details arranged as part of the experience."

    useful: list[str] = []
    for item in includes:
        lower = item.lower()
        if any(skip in lower for skip in ["pick-up", "drop-off", "transfer", "transportation", "guide", "ticket", "tickets", "wifi", "wi-fi"]):
            continue
        useful.append(polish_client_text(item).strip(" ."))
        if len(useful) >= 4:
            break
    if len(useful) < 2:
        return ""
    if len(useful) == 2:
        focus = f"{useful[0]} and {useful[1]}"
    else:
        focus = ", ".join(useful[:-1]) + f" and {useful[-1]}"
    if title:
        return polish_client_text(f"This arranged experience is centred around {focus}, giving the day a clear and memorable focus.")
    return polish_client_text(f"The day includes {focus}, with the arrangements kept clear and easy to follow.")




def safe_generic_description(row: dict) -> str:
    """Last-resort client-facing description that never echoes raw supplier text."""
    title = clean_client_title(row.get("title") or row.get("original_title") or "", row)
    city = canonicalize_place_name(row.get("city", ""))
    lower = f"{title} {row.get('title','')} {row.get('details','')} {row.get('original_title','')}".lower()
    place = f" in {city}" if city else ""
    if "walking tour" in lower or "citywalk" in lower:
        return f"Enjoy a guided walking tour{place}, with local stories and key sights introduced at an easy pace."
    if "munch" in lower and "museum" in lower:
        return "Visit the Munch Museum at your own pace with pre-arranged admission tickets."
    if "fløibanen" in lower or "floibanen" in lower:
        return "Use your round-trip Fløibanen ticket for a flexible visit to Mount Fløyen, with time to enjoy the views over Bergen."
    if "blue lagoon" in lower and "volcano" in lower:
        return "Combine a guided visit to the Fagradalsfjall volcano area with time to relax in the warm geothermal waters of the Blue Lagoon."
    if "blue lagoon" in lower:
        return "Enjoy time at the Blue Lagoon, with admission arranged as part of the day."
    if "northern lights" in lower or "aurora" in lower:
        return "Head out in search of the Northern Lights, with the route adapted to the evening conditions and local guidance included."
    if "ferry" in lower and "tallinn" in lower:
        return "Travel between Helsinki and Tallinn by ferry, with time arranged to experience the historic Old Town."
    if "train" in lower or "rail" in lower:
        return "Continue by rail, with the route and timing arranged as part of the day."
    if "hike" in lower or "hiking" in lower:
        return f"Enjoy a guided outdoor experience{place}, with the route planned around the scenery and pace of the day."
    return f"Enjoy a planned experience{place}, with the key arrangements prepared in advance and the wider day kept easy to follow."


def client_activity_description(row: dict, fallback: str = "") -> str:
    """Compose final premium activity text from facts, not supplier paragraphs."""

    draft = compose_activity_description(row, fallback=fallback)
    return draft.text


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


def group_tour_pickup_window_from_overview(row: dict) -> str:
    if not is_group_tour_overview(row):
        return ""
    text = f"{row.get('title', '')} | {row.get('details', '')} | {row.get('original_title', '')}"
    match = re.search(r"\|\s*(\d{1,2})(?::(\d{2}))?\s*([AaPp]\.?[Mm]\.?)\b", text)
    if not match:
        return ""
    hour = int(match.group(1))
    minute = int(match.group(2) or "0")
    suffix = match.group(3).replace(".", "").upper()
    start = f"{hour}:{minute:02d} {suffix}"
    end_minute = minute + 30
    end_hour = hour + (1 if end_minute >= 60 else 0)
    end_minute %= 60
    if suffix == "PM" and end_hour > 12:
        end_hour -= 12
    return f"Between {start} and {end_hour}:{end_minute:02d} {suffix}"


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
        if "kiruna to stockholm" in full or "kiruna station" in full and "stockholm central" in full:
            return "Overnight train to Stockholm"
        return "Overnight train to Kiruna"
    if "round trip ferry" in full and "tallinn" in full:
        return "Helsinki-Tallinn Ferry"
    if "tickets to the" in full or "ticket" in full and "museum" in full:
        if "munch" in full:
            return "Munch Museum Visit"
    if re.fullmatch(r"city walking tour", text, flags=re.IGNORECASE) and city:
        return f"{city} Walking Tour"
    return polish_title(text)


def sanitize_supplier_prose(value: str, *, max_sentences: int = 4, title: str = "") -> str:
    text = repair_common_supplier_typos(str(value or "").replace("\r\n", "\n").replace("\r", "\n"))
    if not text.strip():
        return ""
    # Remove supplier title/metadata prefix when it is pipe based.
    if "|" in text.split("\n", 1)[0]:
        parts = [part.strip() for part in text.split("|")]
        # Keep fragments after obvious metadata; if no narrative fragments, fall back blank.
        narrative = [p for p in parts if len(p.split()) > 8 and not re.search(r"\b(?:time|hrs?|meeting|includes?|tickets? only)\b", p, re.I)]
        if narrative:
            text = " ".join(narrative)
        else:
            text = ""
    # Prefer sections with narrative.
    for marker in [r"What to expect\??", r"Overview", r"Highlights"]:
        m = re.search(marker + r"\s*(.+)", text, flags=re.I | re.S)
        if m:
            text = m.group(1)
            break
    # Cut at operational sections.
    text = re.split(r"\n\s*(?:What's included|What’s included|Included|Includes|Please note|Booking Information|Not included|Not Included|Meeting Point|Pick up / meeting point|Pick-up / meeting point|Departure:|Duration:|Suitable for:|Age limit:|Gather at:|Carried out:|Participanter:)", text, maxsplit=1, flags=re.I)[0]
    # Drop operational/legal sentences.
    sentences = []
    for sentence in _sentences(text):
        s = sentence.strip(" -:|•")
        if not s:
            continue
        lower = s.lower()
        if any(bad in lower for bad in ["price is per", "supplement", "please arrive", "booking information", "at checkout", "valid driver's license", "min age", "participants", "participanter", "cancel", "stay updated", "calendar", "carried out", "duration:", "meeting point", "what's included", "includes:", "included:", "ticket only", "tickets only", "tickets included", "entry tickets", "what are you waiting", "book your", "check availability", "your guide will be timing", "thirsty?", "just open your mouth", "instant foot wetness"]):
            continue
        if "|" in s:
            continue
        if len(s.split()) < 5 and len(sentences) > 0:
            continue
        sentences.append(s)
        if len(sentences) >= max_sentences:
            break
    result = polish_client_text(" ".join(sentences))
    result = re.sub(r"\bPick-up\b", "pick-up", result) if not result.startswith("Pick-up") else result
    result = re.sub(r"\b2\.\s*5hr\b", "2.5-hour", result, flags=re.I)
    return result


def sanitize_inclusion_item(value: str, title: str = "") -> str:
    item = repair_common_supplier_typos(clean_inline(value)).strip(" •-*|:")
    if not item:
        return ""
    lower = item.lower()
    if lower in {"local", "included", "includes", "what's included", "what’s included", "overview", "description"}:
        return ""
    if any(marker in lower for marker in ["not included", "price", "supplement", "checkout", "book your", "check availability"]):
        return ""
    if has_raw_supplier_residue(item) and len(item.split()) > 10:
        return ""
    item = re.sub(r"^Local,\s*English-speaking guide$", "Local English-speaking guide", item, flags=re.I)
    item = re.sub(r"^English-speaking guide$", "English-speaking guide", item, flags=re.I)
    item = re.sub(r"Thermal clothing \(overalls$", "Thermal clothing (overalls, shoes, wool socks and gloves)", item, flags=re.I)
    return polish_inclusion_item(item, title)


def merge_compound_inclusions(items: list[str]) -> list[str]:
    merged: list[str] = []
    for raw in items:
        item = sanitize_inclusion_item(raw)
        if not item:
            continue
        lower = item.lower().strip(" .")
        if lower == "english-speaking guide" and merged and merged[-1].lower().strip(" .") in {"local", "experienced"}:
            prefix = merged[-1].strip(" .")
            merged[-1] = f"{prefix} English-speaking guide"
            continue
        if lower == "personal experience" and merged and merged[-1].lower().strip(" .") == "live host for a fun":
            merged[-1] = "Live host for a fun, personal experience"
            continue
        if lower in {"shoes", "gloves", "wool socks", "shoes, wool socks, gloves)"} and merged and "thermal clothing" in merged[-1].lower():
            if item.lower() not in merged[-1].lower():
                merged[-1] = merged[-1].rstrip(" .)") + f", {item})"
            continue
        if item not in merged:
            merged.append(item)
    return polish_inclusion_items(merged)



def sanitize_day_intro(value: str, rows: list[dict] | None = None) -> str:
    """Final day-intro sanitizer used by the canonical day builder."""
    text = polish_client_text(repair_common_supplier_typos(value or ""))
    if not text:
        return ""
    text = re.sub(r"\bThe arrangements in ([^,.]+) are designed to keep the day smooth and comfortable, with the key logistics handled clearly\.", r"Today's arrangements in \1 are kept clear, comfortable and easy to follow.", text, flags=re.I)
    text = re.sub(r"\bThe day’s arrangements are listed below\.\b", "Today's arrangements are listed below.", text, flags=re.I)
    text = re.sub(r"\bYour guided tour begins today\.\s*Your guided group tour", "Your guided group tour", text, flags=re.I)
    return text


_INTERNAL_NOTE_MARKERS = [
    "there are 2 options", "right now we have included", "cheaper version", "note :", "note:",
    "internal", "supplier note", "operator note", "sales note",
]


def is_internal_note_text(value: str) -> bool:
    lower = str(value or "").lower()
    return any(marker in lower for marker in _INTERNAL_NOTE_MARKERS)


def sanitize_display_text(value: str, *, max_sentences: int = 4) -> str:
    """Strict generic display-text sanitizer for any late-bound renderer text."""
    return sanitize_supplier_prose(value, max_sentences=max_sentences)

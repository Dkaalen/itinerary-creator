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
from text_polish import polish_client_text, polish_title, strip_price_fragments


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
    return polish_client_text(" ".join(useful))


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
            return polish_client_text(" ".join(useful))
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


def client_activity_description(row: dict, fallback: str = "") -> str:
    """Final description rule: real row text first, generic fallback last.

    Group-tour supplier day rows are never allowed to fall back to unrelated
    known-product copy if the supplier row contains useful day-specific prose.
    """

    explicit = polish_client_text(row.get("client_description") or "")
    if explicit:
        return explicit
    own_text = supplier_activity_body(row, max_sentences=12 if is_supplier_day_row(row) else 4)
    if own_text:
        return own_text
    included_description = _description_from_included_items(row)
    if included_description:
        return included_description
    return polish_client_text(fallback)


def clean_admin_title_fragment(value: str) -> str:
    text = strip_price_fragments(clean_inline(value))
    text = re.sub(r"^Accommodation\s*:\s*Check[- ]?in\s+at\s+", "", text, flags=re.IGNORECASE).strip(" -:|")
    text = re.sub(r"^Check[- ]?in\s+at\s+", "", text, flags=re.IGNORECASE).strip(" -:|")
    text = re.sub(r"\s+(?:with|incl\.?|including)\s+transfers?\b", "", text, flags=re.IGNORECASE).strip(" -:|")
    text = re.sub(r"\bWatch\s+Whales\b", "Whale Watching", text, flags=re.IGNORECASE)
    return polish_title(text)


def cleaned_generic_activity_title(title: str, row: dict | None = None) -> str:
    row = row or {}
    text = clean_admin_title_fragment(title)
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

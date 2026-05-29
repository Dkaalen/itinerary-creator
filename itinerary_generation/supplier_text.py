"""Supplier prose extraction helpers for client-facing itinerary content."""

from __future__ import annotations

import re

from itinerary_generation.content_text import _sentences, _trim_supplier_sections, row_text
from itinerary_generation.display_text_safety import sanitize_supplier_prose


def is_group_tour_overview(row: dict) -> bool:
    text = row_text(row).lower()
    return (row.get("effective_type") or row.get("type", "")) == "Day Overview" and any(
        marker in text for marker in ["group tour", "holiday package", "sharing room basis"]
    )


def is_supplier_day_row(row: dict) -> bool:
    source = str(row.get("details") or row.get("original_title") or row.get("title") or "")
    return bool(re.match(r"^\s*Day\s+\d+\s*[:\-–]", source, flags=re.IGNORECASE))


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

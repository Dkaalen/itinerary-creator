"""Sanitizers for late-bound client-facing prose."""

from __future__ import annotations

import re

from text_polish import polish_client_text
from itinerary_generation.content_text import _sentences
from itinerary_generation.title_cleanup import repair_common_supplier_typos


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

"""Source cleaning helpers for activity description composition."""

from __future__ import annotations

import re

from text_polish import polish_title

from itinerary_generation.description_patterns import STOP_SOURCE_SECTION_RE, TYPO_FIXES


def _clean_inline(value: object) -> str:
    text = str(value or "").replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")
    for pattern, replacement in TYPO_FIXES:
        text = re.sub(pattern, replacement, text, flags=re.I)
    text = re.sub(r"\b2\.\s*5\s*hr\b", "2.5-hour", text, flags=re.I)
    text = re.sub(r"\b(\d+)\.\s*(\d+)\s*hr\b", r"\1.\2-hour", text, flags=re.I)
    return text.strip()


def _row_source(row: dict) -> str:
    parts = [row.get("details", ""), row.get("original_title", ""), row.get("title", "")]
    return _clean_inline("\n".join(str(part or "") for part in parts if str(part or "").strip()))


def _title(row: dict) -> str:
    raw = row.get("display_title") or row.get("title") or row.get("original_title") or "included experience"
    text = str(raw or "")
    text = re.sub(r"^\s*Day\s+\d+\s*[:\-–]\s*", "", text, flags=re.I)
    text = re.sub(r"\s*\|.*$", "", text).strip(" -:|")
    text = re.sub(r"^\s*[A-Za-zÀ-ÿ ]+\s*:\s*", "", text) if len(text.split(":", 1)[0].split()) <= 3 else text
    return polish_title(text or "included experience")


def _is_group_day(row: dict) -> bool:
    src = str(row.get("details") or row.get("original_title") or row.get("title") or "")
    return bool(re.match(r"^\s*Day\s+\d+\s*[:\-–]", src, flags=re.I))


def _narrative_source(row: dict) -> str:
    source = _row_source(row)
    # Prefer narrative sections when present, then strip heading/metadata.
    for marker in [r"What to expect\??", r"Overview", r"Highlights"]:
        match = re.search(marker + r"\s*(.+)", source, flags=re.I | re.S)
        if match:
            source = match.group(1)
            break
    source = re.sub(r"^\s*Day\s+\d+\s*[:\-–]\s*[^\n]+", "", source, count=1, flags=re.I).strip()
    source = STOP_SOURCE_SECTION_RE.split(source, maxsplit=1)[0]
    # Remove leading pipe metadata lines.
    if "|" in source.split("\n", 1)[0]:
        parts = [p.strip() for p in re.split(r"\s*\|\s*", source) if p.strip()]
        source = " ".join(p for p in parts if len(p.split()) > 7 and not re.search(r"\b(?:time|hrs?|meeting|includes?|tickets? only)\b", p, re.I))
    return source.strip()



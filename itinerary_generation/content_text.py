"""Small text helpers shared by itinerary content modules."""

from __future__ import annotations

import re


def clean_inline(value: str) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


def row_text(row: dict) -> str:
    return f"{row.get('title', '')}\n{row.get('original_title', '')}\n{row.get('details', '')}"


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

"""Structured accommodation-specific inclusions from supplier hotel rows."""

from __future__ import annotations

import re

from text_polish import polish_client_text


_STOP_MARKERS = (
    "not included",
    "what's not included",
    "what’s not included",
    "important information",
    "important info",
    "please note",
)


def extract_stay_inclusions(row: dict) -> list[str]:
    """Return inclusions explicitly listed under an accommodation stay marker.

    Hotel rows sometimes contain experience-like benefits that cannot be
    reconstructed from room category or meal-plan fields.  Only text after an
    explicit ``Included in your stay`` marker is used, so ordinary hotel prose
    is not promoted into guaranteed services.
    """

    source = ""
    match = None
    for key in ("details", "original_title", "title"):
        candidate = str(row.get(key, "") or "").replace("\r\n", "\n").replace("\r", "\n")
        candidate_match = re.search(r"included\s+in\s+your\s+stay\s*:?", candidate, flags=re.IGNORECASE)
        if candidate_match:
            source = candidate
            match = candidate_match
            break
    if match is None:
        return []

    section = source[match.end():]
    items: list[str] = []
    for raw_line in section.splitlines():
        line = raw_line.strip(" \t•*-–—")
        if not line:
            continue
        lower = line.lower().strip(" :")
        if any(lower.startswith(marker) for marker in _STOP_MARKERS):
            break
        cleaned = polish_client_text(line).strip(" .")
        if cleaned and cleaned.lower() not in {item.lower() for item in items}:
            items.append(cleaned)
    return items


__all__ = ["extract_stay_inclusions"]

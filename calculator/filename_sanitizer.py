"""Safe filenames for calculator workbook downloads."""

from __future__ import annotations

import re

_DEFAULT_STEM = "Itinerary"
_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WHITESPACE = re.compile(r"\s+")
_MAX_STEM_LENGTH = 140


def sanitize_filename_stem(value: str, fallback: str = _DEFAULT_STEM) -> str:
    """Return a Windows-safe filename stem without an extension."""

    cleaned = _INVALID_FILENAME_CHARS.sub(" ", str(value or ""))
    cleaned = _WHITESPACE.sub(" ", cleaned).strip(" .")
    if not cleaned:
        cleaned = fallback
    return cleaned[:_MAX_STEM_LENGTH].rstrip(" .") or fallback


def calculation_workbook_filename(itinerary_name: str) -> str:
    """Return the standard exported calculation workbook filename."""

    return f"{sanitize_filename_stem(itinerary_name)} - Calculation.xlsx"

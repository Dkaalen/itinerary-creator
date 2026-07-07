"""PDF download filename helpers."""

from __future__ import annotations

from collections.abc import Mapping

from app_modules.itinerary_name_state import itinerary_name_from_state
from calculator.filename_sanitizer import sanitize_filename_stem


def pdf_filename_stem_from_state(state: Mapping[str, object]) -> str:
    """Return a safe PDF filename stem using the itinerary name first."""

    name = itinerary_name_from_state(state)
    return sanitize_filename_stem(name, fallback="Itinerary")

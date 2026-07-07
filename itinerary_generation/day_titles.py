"""Compatibility facade for day titles.

Title Brain is the single owner of client-facing day headings. This module keeps
the historical import path stable without carrying fallback title logic.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from itinerary_generation.title_brain import write_day_title


def create_day_title(day_rows: Sequence[Mapping[str, Any]] | None, *, visit_context: object | None = None) -> str:
    """Return the Title Brain day heading for the supplied rows."""

    return write_day_title(day_rows or (), visit_context=visit_context)


__all__ = ["create_day_title"]

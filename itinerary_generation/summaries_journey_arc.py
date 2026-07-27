"""Compatibility facade for journey-overview chapters."""

from __future__ import annotations

from itinerary_generation.journey_overview_brain import create_journey_overview, format_day_range


def create_journey_arc(grouped_days, *, continuity_report=None):
    """Return summary-page journey chapters.

    Kept under the historical function name for public compatibility; the
    ownership now lives in ``journey_overview_brain``.
    """

    return create_journey_overview(grouped_days, continuity_report=continuity_report)


__all__ = ["create_journey_arc", "format_day_range"]

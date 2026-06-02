"""Compatibility facade for structural itinerary validation."""

from __future__ import annotations

from itinerary_generation.quality_gate import (
    ItineraryQualityGateReport,
    ItineraryQualitySnapshot,
    ItineraryValidationIssue,
    blocking_validation_messages,
    build_quality_snapshot,
    evaluate_itinerary_quality,
    validate_itinerary_integrity,
)

__all__ = [
    "ItineraryQualityGateReport",
    "ItineraryQualitySnapshot",
    "ItineraryValidationIssue",
    "blocking_validation_messages",
    "build_quality_snapshot",
    "evaluate_itinerary_quality",
    "validate_itinerary_integrity",
]

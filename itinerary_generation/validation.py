"""Compatibility facade for structural itinerary validation."""

from __future__ import annotations

from itinerary_generation.quality_gate import (
    ItineraryQualityGateReport,
    ItineraryQualitySnapshot,
    ItineraryValidationIssue,
    blocking_client_output_messages,
    blocking_validation_messages,
    build_quality_snapshot,
    evaluate_client_output_quality,
    evaluate_itinerary_quality,
    render_document_text,
    validate_itinerary_integrity,
)

__all__ = [
    "ItineraryQualityGateReport",
    "ItineraryQualitySnapshot",
    "ItineraryValidationIssue",
    "blocking_client_output_messages",
    "blocking_validation_messages",
    "build_quality_snapshot",
    "evaluate_client_output_quality",
    "evaluate_itinerary_quality",
    "render_document_text",
    "validate_itinerary_integrity",
]

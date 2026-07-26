"""Compatibility facade for quality gates."""

from __future__ import annotations

from itinerary_generation.quality_gate_core import (
    IMPORTANT_ROW_TYPES,
    ItineraryValidationIssue,
    ItineraryQualitySnapshot,
    ItineraryQualityGateReport,
    ClientOutputQualityGateReport,
    build_quality_snapshot,
    evaluate_itinerary_quality,
    validate_itinerary_integrity,
    blocking_validation_messages,
    evaluate_prepared_client_output_quality,
    add_image_quality_issues,
    evaluate_client_output_quality,
    blocking_client_output_messages,
    render_document_text,
    raw_supplier_scan_text,
)

__all__ = ['IMPORTANT_ROW_TYPES', 'ItineraryValidationIssue', 'ItineraryQualitySnapshot', 'ItineraryQualityGateReport', 'ClientOutputQualityGateReport', 'build_quality_snapshot', 'evaluate_itinerary_quality', 'validate_itinerary_integrity', 'blocking_validation_messages', 'evaluate_prepared_client_output_quality', 'add_image_quality_issues', 'evaluate_client_output_quality', 'blocking_client_output_messages', 'render_document_text', 'raw_supplier_scan_text']

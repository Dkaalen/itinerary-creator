"""Compatibility facade for itinerary quality gates.

Named quality-gate modules own the real responsibilities. This module keeps
older imports stable while preventing ``quality_gate_core.py`` from becoming a
catch-all implementation file again.
"""

from __future__ import annotations

from itinerary_generation.generation_quality_gate import (
    IMPORTANT_ROW_TYPES,
    BLOCKING,
    WARNING,
    ItineraryValidationIssue,
    ItineraryQualitySnapshot,
    ItineraryQualityGateReport,
    _as_rows,
    _max_day,
    _is_important_row,
    _important_rows,
    build_quality_snapshot,
    _validate_snapshot,
    _source_fidelity_issues,
    evaluate_itinerary_quality,
    validate_itinerary_integrity,
    blocking_validation_messages,
)
from itinerary_generation.client_output_quality_gate import (
    ClientOutputQualityGateReport,
    _append_text,
    render_document_text,
    raw_supplier_scan_text,
    _meta_lines_with_time_warnings,
    _journey_arc_phrase_issues,
    _bare_activity_blocks,
    _image_payload_is_default,
    _image_match_issues,
    _image_bank_status_issues,
    evaluate_client_output_quality,
    blocking_client_output_messages,
)
from itinerary_generation.quality_gate_patterns import (
    FORBIDDEN_CLIENT_PATTERNS,
    AURORA_REVIEW_PATTERN,
    PRICE_CLIENT_PATTERN_MESSAGE,
    SUPPLIER_TIME_WARNING_RE,
    SUSPICIOUS_AM_PM_TIME_RANGE_RE,
    RAW_SUPPLIER_FIELD_RE,
)

__all__ = [
    "IMPORTANT_ROW_TYPES",
    "BLOCKING",
    "WARNING",
    "ItineraryValidationIssue",
    "ItineraryQualitySnapshot",
    "ItineraryQualityGateReport",
    "ClientOutputQualityGateReport",
    "_as_rows",
    "_max_day",
    "_is_important_row",
    "_important_rows",
    "build_quality_snapshot",
    "_validate_snapshot",
    "_source_fidelity_issues",
    "evaluate_itinerary_quality",
    "validate_itinerary_integrity",
    "blocking_validation_messages",
    "FORBIDDEN_CLIENT_PATTERNS",
    "AURORA_REVIEW_PATTERN",
    "PRICE_CLIENT_PATTERN_MESSAGE",
    "SUPPLIER_TIME_WARNING_RE",
    "SUSPICIOUS_AM_PM_TIME_RANGE_RE",
    "RAW_SUPPLIER_FIELD_RE",
    "_append_text",
    "render_document_text",
    "raw_supplier_scan_text",
    "_meta_lines_with_time_warnings",
    "_journey_arc_phrase_issues",
    "_bare_activity_blocks",
    "_image_payload_is_default",
    "_image_match_issues",
    "_image_bank_status_issues",
    "evaluate_client_output_quality",
    "blocking_client_output_messages",
]

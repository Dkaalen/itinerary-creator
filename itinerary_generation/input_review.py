"""Compatibility facade for structured input review helpers."""

from __future__ import annotations

from itinerary_generation.input_review_builder import build_structured_input_review
from itinerary_generation.input_review_corrections import (
    _canonical_destination_name,
    _correction_field_updates,
    apply_input_correction_actions,
    build_input_correction_actions,
)
from itinerary_generation.input_review_formatting import format_structured_input_review
from itinerary_generation.input_review_helpers import _confidence, _rows, _text
from itinerary_generation.input_review_models import (
    StructuredInputCorrectionAction,
    StructuredInputReview,
    StructuredInputRowReview,
)
from itinerary_generation.input_review_rows import (
    _confidence_label,
    _destination_status,
    _missing_fields,
    _next_action,
    _primary_fix,
    _review_priority,
    _row_title,
    _status,
    _suggested_fixes,
    build_input_row_reviews,
)

__all__ = (
    "StructuredInputRowReview",
    "StructuredInputCorrectionAction",
    "StructuredInputReview",
    "_rows",
    "_text",
    "_confidence",
    "_missing_fields",
    "_destination_status",
    "_confidence_label",
    "_suggested_fixes",
    "_primary_fix",
    "_review_priority",
    "_next_action",
    "_status",
    "_row_title",
    "build_input_row_reviews",
    "_canonical_destination_name",
    "_correction_field_updates",
    "build_input_correction_actions",
    "apply_input_correction_actions",
    "build_structured_input_review",
    "format_structured_input_review",
)

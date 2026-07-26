"""Orchestrate late validation of generated client-facing output."""

from __future__ import annotations

import re
from typing import Any, Mapping

from itinerary_generation.advisor_quality_checks import advisor_quality_issues
from itinerary_generation.client_copy_sanitation import contains_customer_copy_violation
from itinerary_generation.client_quality_content_checks import (
    bare_activity_blocks as _bare_activity_blocks,
    journey_arc_phrase_issues as _journey_arc_phrase_issues,
    meta_lines_with_time_warnings as _meta_lines_with_time_warnings,
)
from itinerary_generation.client_quality_images import (
    image_bank_status_issues as _image_bank_status_issues,
    image_match_issues as _image_match_issues,
    image_payload_is_default as _image_payload_is_default,
)
from itinerary_generation.client_quality_report import (
    ClientOutputQualityGateReport,
    build_client_output_quality_report,
    extend_client_output_quality_report,
)
from itinerary_generation.client_quality_text import (
    append_text as _append_text,
    raw_supplier_scan_text,
    render_document_text,
)
from itinerary_generation.client_quality_truth_checks import client_truth_issues
from itinerary_generation.client_sanitizer import contains_price_or_currency
from itinerary_generation.generation_quality_gate import BLOCKING, WARNING, ItineraryValidationIssue
from itinerary_generation.quality_gate_patterns import (
    AURORA_REVIEW_PATTERN,
    FORBIDDEN_CLIENT_PATTERNS,
    PRICE_CLIENT_PATTERN_MESSAGE,
    RAW_SUPPLIER_FIELD_RE,
    SUSPICIOUS_AM_PM_TIME_RANGE_RE,
)


def _prepared_document_issues(render_document: Any, *, source_rows: Any = None) -> list[ItineraryValidationIssue]:
    """Evaluate document and source-backed rules exactly once per prepared document."""

    issues: list[ItineraryValidationIssue] = []
    text = render_document_text(render_document)
    for code, pattern, message in FORBIDDEN_CLIENT_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            issues.append(ItineraryValidationIssue(BLOCKING, code, message))
    if AURORA_REVIEW_PATTERN.search(text):
        issues.append(
            ItineraryValidationIssue(
                WARNING,
                "aurora_wording_review",
                "Client-facing output contains 'Aurora'. Verify it is preserved supplier/product wording; otherwise prefer 'Northern Lights'.",
            )
        )
    if SUSPICIOUS_AM_PM_TIME_RANGE_RE.search(text):
        issues.append(
            ItineraryValidationIssue(
                WARNING,
                "suspicious_am_pm_time_range",
                "Client-facing output contains a suspicious AM-to-PM time range. Review the source timing before sending to the client.",
            )
        )
    if contains_price_or_currency(text):
        issues.append(ItineraryValidationIssue(BLOCKING, "client_price_or_currency_leak", PRICE_CLIENT_PATTERN_MESSAGE))
    if RAW_SUPPLIER_FIELD_RE.search(raw_supplier_scan_text(render_document)):
        issues.append(
            ItineraryValidationIssue(
                BLOCKING,
                "raw_supplier_field_leak",
                "Raw supplier section labels leaked into generated client output.",
            )
        )
    for context in _meta_lines_with_time_warnings(render_document):
        issues.append(
            ItineraryValidationIssue(
                BLOCKING,
                "supplier_warning_in_time_field",
                "Supplier warning text leaked into a Time field.",
                context=context,
            )
        )
    for context in _bare_activity_blocks(render_document):
        issues.append(
            ItineraryValidationIssue(
                BLOCKING,
                "bare_activity_inclusion_heading",
                "Activity block has a heading but no supporting client-facing text.",
                context=context,
            )
        )
    if contains_customer_copy_violation(text):
        issues.append(
            ItineraryValidationIssue(
                BLOCKING,
                "customer_copy_sanitation_bypass",
                "Unsanitized placeholder, duplicate label/article, or supplier administration remains in client output.",
            )
        )
    issues.extend(_journey_arc_phrase_issues(render_document))
    issues.extend(client_truth_issues(render_document, source_rows=source_rows))
    issues.extend(advisor_quality_issues(render_document, source_rows=source_rows))
    return issues


def evaluate_prepared_client_output_quality(
    render_document: Any,
    *,
    source_rows: Any = None,
) -> ClientOutputQualityGateReport:
    """Build the canonical non-image quality report for a prepared document."""

    return build_client_output_quality_report(
        _prepared_document_issues(render_document, source_rows=source_rows)
    )


def add_image_quality_issues(
    report: ClientOutputQualityGateReport,
    *,
    day_images: Mapping | None = None,
    image_bank_status: Mapping[str, Any] | None = None,
) -> ClientOutputQualityGateReport:
    """Add image-state findings without reevaluating prepared document rules."""

    return extend_client_output_quality_report(
        report,
        (
            *_image_match_issues(day_images),
            *_image_bank_status_issues(image_bank_status),
        ),
    )


def evaluate_client_output_quality(
    render_document: Any,
    *,
    day_images: Mapping | None = None,
    image_bank_status: Mapping[str, Any] | None = None,
    source_rows: Any = None,
) -> ClientOutputQualityGateReport:
    """Compatibility entry point for callers without a prepared report."""

    report = evaluate_prepared_client_output_quality(render_document, source_rows=source_rows)
    return add_image_quality_issues(
        report,
        day_images=day_images,
        image_bank_status=image_bank_status,
    )


def blocking_client_output_messages(render_document: Any, **kwargs: Any) -> list[str]:
    return [issue.message for issue in evaluate_client_output_quality(render_document, **kwargs).blocking_issues]


__all__ = [
    "ClientOutputQualityGateReport",
    "_append_text",
    "render_document_text",
    "raw_supplier_scan_text",
    "_meta_lines_with_time_warnings",
    "_journey_arc_phrase_issues",
    "_bare_activity_blocks",
    "_image_payload_is_default",
    "_image_match_issues",
    "_image_bank_status_issues",
    "evaluate_prepared_client_output_quality",
    "add_image_quality_issues",
    "evaluate_client_output_quality",
    "blocking_client_output_messages",
]

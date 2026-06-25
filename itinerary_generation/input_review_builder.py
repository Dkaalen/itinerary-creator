"""Build full structured input review summaries."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping

from itinerary_generation.common import group_rows_by_day
from itinerary_generation.input_review_corrections import build_input_correction_actions
from itinerary_generation.input_review_helpers import _rows
from itinerary_generation.input_review_models import StructuredInputReview
from itinerary_generation.input_review_rows import build_input_row_reviews
from itinerary_generation.itinerary_health_checks import build_itinerary_health_issues, summarize_itinerary_health_issues
from itinerary_generation.row_filters import get_row_type, is_optional_row
from itinerary_generation.row_sequence import ordered_cities


def build_structured_input_review(
    parsed_rows: Iterable[Mapping[str, Any]] | None,
    *,
    parser_diagnostics: Iterable[Mapping[str, Any]] | None = None,
) -> StructuredInputReview:
    rows = _rows(parsed_rows)
    main_rows = [row for row in rows if not is_optional_row(row)]
    grouped = group_rows_by_day(rows)

    service_counts = Counter(get_row_type(row) or "Other" for row in rows)
    day_counts: dict[str, dict[str, int]] = {}
    for day, day_rows in grouped.items():
        day_counts[str(day)] = dict(Counter(get_row_type(row) or "Other" for row in day_rows))

    issues = build_itinerary_health_issues(rows, parser_diagnostics=parser_diagnostics)
    summary = summarize_itinerary_health_issues(issues)
    row_reviews = build_input_row_reviews(rows)
    confidences = [row.confidence for row in row_reviews]
    average_confidence = round(sum(confidences) / len(confidences)) if confidences else 100
    review_flags = Counter(
        flag
        for row in rows
        for flag in (row.get("parser_review_flags") or [])
        if str(flag or "").strip()
    )
    low_confidence_count = sum(1 for row in row_reviews if row.status != "Ready")
    suggested_fix_count = sum(1 for row in row_reviews if row.suggested_fixes)
    correction_actions = build_input_correction_actions(rows)

    return StructuredInputReview(
        row_count=len(rows),
        day_count=len(grouped),
        route=ordered_cities(main_rows),
        service_counts=dict(sorted(service_counts.items())),
        day_service_counts=day_counts,
        issue_count=summary.total,
        critical_issue_count=summary.critical,
        review_issue_count=summary.review,
        status_label=summary.status_label,
        average_confidence=average_confidence,
        low_confidence_count=low_confidence_count,
        suggested_fix_count=suggested_fix_count,
        review_flags=dict(sorted(review_flags.items())),
        row_reviews=row_reviews,
        correction_actions=correction_actions,
        issues=issues,
    )

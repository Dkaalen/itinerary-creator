"""Structured input review for parsed supplier rows."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from itinerary_generation.common import group_rows_by_day
from itinerary_generation.itinerary_health_checks import (
    ItineraryHealthIssue,
    build_itinerary_health_issues,
    summarize_itinerary_health_issues,
)
from itinerary_generation.row_filters import get_row_type, is_optional_row
from itinerary_generation.row_sequence import ordered_cities


@dataclass(frozen=True)
class StructuredInputReview:
    row_count: int
    day_count: int
    route: tuple[str, ...]
    service_counts: dict[str, int]
    day_service_counts: dict[str, dict[str, int]]
    issue_count: int
    critical_issue_count: int
    review_issue_count: int
    status_label: str
    average_confidence: int = 100
    review_flags: dict[str, int] | None = None
    issues: tuple[ItineraryHealthIssue, ...] = ()

    @property
    def route_text(self) -> str:
        return " → ".join(self.route) if self.route else "Not detected"

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["issues"] = [issue.as_dict() for issue in self.issues]
        data["route"] = list(self.route)
        return data


def _rows(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    return [dict(row) for row in rows or [] if isinstance(row, Mapping)]


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
    confidences = [int(row.get("parser_confidence", 100)) for row in rows if str(row.get("parser_confidence", "")).isdigit()]
    average_confidence = round(sum(confidences) / len(confidences)) if confidences else 100
    review_flags = Counter(
        flag
        for row in rows
        for flag in (row.get("parser_review_flags") or [])
        if str(flag or "").strip()
    )

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
        review_flags=dict(sorted(review_flags.items())),
        issues=issues,
    )


def format_structured_input_review(review: StructuredInputReview) -> str:
    counts = ", ".join(f"{label}: {count}" for label, count in review.service_counts.items()) or "none"
    lines = [
        "Structured Input Review",
        f"Status: {review.status_label}",
        f"Rows: {review.row_count}",
        f"Days: {review.day_count}",
        f"Route: {review.route_text}",
        f"Services: {counts}",
        f"Parser confidence: {review.average_confidence}%",
        f"Issues: {review.critical_issue_count} critical / {review.review_issue_count} review / {review.issue_count} total",
    ]
    if review.review_flags:
        flags = ", ".join(f"{label}: {count}" for label, count in review.review_flags.items())
        lines.append(f"Review flags: {flags}")
    for issue in review.issues[:12]:
        prefix = f"{issue.day}: " if issue.day else ""
        lines.append(f"- [{issue.severity}] {prefix}{issue.message}")
    return "\n".join(lines)

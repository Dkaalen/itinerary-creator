"""Structured input review for parsed supplier rows."""

from __future__ import annotations

from collections import Counter
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
class StructuredInputRowReview:
    row_number: int
    day: str
    service_type: str
    city: str
    title: str
    confidence: int
    status: str
    flags: tuple[str, ...] = ()
    missing_fields: tuple[str, ...] = ()
    suggested_fixes: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["flags"] = list(self.flags)
        data["missing_fields"] = list(self.missing_fields)
        data["suggested_fixes"] = list(self.suggested_fixes)
        return data


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
    low_confidence_count: int = 0
    suggested_fix_count: int = 0
    review_flags: dict[str, int] | None = None
    row_reviews: tuple[StructuredInputRowReview, ...] = ()
    issues: tuple[ItineraryHealthIssue, ...] = ()

    @property
    def route_text(self) -> str:
        return " → ".join(self.route) if self.route else "Not detected"

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["issues"] = [issue.as_dict() for issue in self.issues]
        data["route"] = list(self.route)
        data["row_reviews"] = [row.as_dict() for row in self.row_reviews]
        return data


def _rows(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    return [dict(row) for row in rows or [] if isinstance(row, Mapping)]


def _text(row: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = str(row.get(key, "") or "").strip()
        if value:
            return value
    return ""


def _confidence(row: Mapping[str, Any]) -> int:
    value = row.get("parser_confidence", 100)
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return 100


def _missing_fields(flags: Iterable[str]) -> tuple[str, ...]:
    labels = {
        "missing_city": "City / destination",
        "missing_hotel_name": "Hotel name",
        "missing_hotel_nights": "Hotel nights",
        "missing_room_category": "Room category",
        "missing_route_origin": "Route origin",
        "missing_route_destination": "Route destination",
        "missing_activity_title": "Activity title",
    }
    return tuple(labels[flag] for flag in flags if flag in labels)


def _suggested_fixes(row: Mapping[str, Any], flags: tuple[str, ...]) -> tuple[str, ...]:
    fixes: list[str] = []
    service_type = get_row_type(row) or "Other"
    declared_type = _text(row, "type")
    effective_type = _text(row, "effective_type")
    if declared_type and effective_type and declared_type != effective_type:
        fixes.append(f"Review row type correction: {declared_type} → {effective_type}.")
    if "missing_city" in flags:
        fixes.append("Confirm the destination before generation.")
    if "missing_hotel_name" in flags:
        fixes.append("Add the hotel name or mark the row as accommodation TBD.")
    if "missing_hotel_nights" in flags:
        fixes.append("Add the number of nights/check-out logic.")
    if "missing_route_origin" in flags or "missing_route_destination" in flags:
        fixes.append("Confirm from/to points for this transport row.")
    if "missing_activity_title" in flags or "weak_title" in flags:
        fixes.append("Give this activity a clear client-facing title.")
    if "very_long_supplier_text" in flags:
        fixes.append("Review long supplier prose for leaked booking/admin text.")
    if not fixes and _confidence(row) < 90:
        fixes.append(f"Review parsed {service_type.lower()} fields before polishing.")

    seen: set[str] = set()
    unique: list[str] = []
    for fix in fixes:
        if fix not in seen:
            seen.add(fix)
            unique.append(fix)
    return tuple(unique)


def _status(confidence: int, flags: tuple[str, ...]) -> str:
    critical_flags = {
        "missing_hotel_name",
        "missing_route_destination",
        "missing_activity_title",
    }
    if confidence < 70 or any(flag in critical_flags for flag in flags):
        return "Check before generation"
    if confidence < 90 or flags:
        return "Needs review"
    return "Ready"


def _row_title(row: Mapping[str, Any]) -> str:
    return _text(row, "title", "original_title", "hotel_name", "name") or "Untitled row"


def build_input_row_reviews(rows: Iterable[Mapping[str, Any]] | None) -> tuple[StructuredInputRowReview, ...]:
    """Return row-level supplier input review records for an import table."""

    reviews: list[StructuredInputRowReview] = []
    for index, row in enumerate(_rows(rows), start=1):
        flags = tuple(str(flag) for flag in (row.get("parser_review_flags") or []) if str(flag or "").strip())
        confidence = _confidence(row)
        reviews.append(
            StructuredInputRowReview(
                row_number=index,
                day=_text(row, "day") or "Unassigned",
                service_type=get_row_type(row) or "Other",
                city=_text(row, "city", "destination", "route_destination", "to") or "Not detected",
                title=_row_title(row),
                confidence=confidence,
                status=_status(confidence, flags),
                flags=flags,
                missing_fields=_missing_fields(flags),
                suggested_fixes=_suggested_fixes(row, flags),
            )
        )
    return tuple(reviews)


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
        f"Rows needing review: {review.low_confidence_count}",
        f"Suggested fixes: {review.suggested_fix_count}",
        f"Issues: {review.critical_issue_count} critical / {review.review_issue_count} review / {review.issue_count} total",
    ]
    if review.review_flags:
        flags = ", ".join(f"{label}: {count}" for label, count in review.review_flags.items())
        lines.append(f"Review flags: {flags}")
    for row in review.row_reviews[:8]:
        if row.status == "Ready":
            continue
        fixes = "; ".join(row.suggested_fixes) if row.suggested_fixes else "Review parsed fields"
        lines.append(f"- Row {row.row_number} [{row.status}] {row.day} · {row.service_type}: {fixes}")
    for issue in review.issues[:12]:
        prefix = f"{issue.day}: " if issue.day else ""
        lines.append(f"- [{issue.severity}] {prefix}{issue.message}")
    return "\n".join(lines)

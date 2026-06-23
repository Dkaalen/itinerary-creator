"""Structured input review for parsed supplier rows."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from itinerary_generation.common import group_rows_by_day
from itinerary_generation.destination_registry import destination_for_alias
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
    confidence_label: str
    status: str
    review_priority: str
    destination_status: str
    primary_fix: str
    next_action: str
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
class StructuredInputCorrectionAction:
    row_number: int
    action_type: str
    action_label: str
    safe_auto_apply: bool
    field_updates: dict[str, Any]
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


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
    correction_actions: tuple[StructuredInputCorrectionAction, ...] = ()
    issues: tuple[ItineraryHealthIssue, ...] = ()

    @property
    def route_text(self) -> str:
        return " → ".join(self.route) if self.route else "Not detected"

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["issues"] = [issue.as_dict() for issue in self.issues]
        data["route"] = list(self.route)
        data["row_reviews"] = [row.as_dict() for row in self.row_reviews]
        data["correction_actions"] = [action.as_dict() for action in self.correction_actions]
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


def _destination_status(city: str) -> str:
    text = str(city or "").strip()
    if not text or text == "Not detected":
        return "Not detected"
    if destination_for_alias(text) is not None:
        return "Known destination"
    return "Confirm destination"


def _confidence_label(confidence: int) -> str:
    if confidence < 70:
        return "Low"
    if confidence < 90:
        return "Medium"
    return "High"


def _suggested_fixes(row: Mapping[str, Any], flags: tuple[str, ...], destination_status: str = "") -> tuple[str, ...]:
    fixes: list[str] = []
    service_type = get_row_type(row) or "Other"
    declared_type = _text(row, "type")
    effective_type = _text(row, "effective_type")
    if declared_type and effective_type and declared_type != effective_type:
        fixes.append(f"Review row type correction: {declared_type} → {effective_type}.")
    if "missing_city" in flags:
        fixes.append("Confirm the destination before generation.")
    if destination_status == "Confirm destination":
        fixes.append("Confirm destination spelling or add it to the registry.")
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


def _primary_fix(fixes: tuple[str, ...]) -> str:
    return fixes[0] if fixes else "No action needed"


def _review_priority(status: str, confidence: int) -> str:
    if status == "Check before generation":
        return "Blocker"
    if status == "Needs review" or confidence < 90:
        return "Review"
    return "Ready"


def _next_action(row: Mapping[str, Any], status: str, fixes: tuple[str, ...], destination_status: str) -> str:
    declared_type = _text(row, "type")
    effective_type = _text(row, "effective_type")
    if declared_type and effective_type and declared_type != effective_type:
        return f"Accept type: {effective_type}"
    if destination_status == "Confirm destination":
        return "Confirm destination"
    if status == "Check before generation":
        return "Fill required field"
    if fixes:
        return "Review suggestion"
    return "No action"


def _status(confidence: int, flags: tuple[str, ...], destination_status: str = "") -> str:
    critical_flags = {
        "missing_hotel_name",
        "missing_route_destination",
        "missing_activity_title",
    }
    if confidence < 70 or any(flag in critical_flags for flag in flags):
        return "Check before generation"
    if confidence < 90 or flags or destination_status == "Confirm destination":
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
        city = _text(row, "city", "destination", "route_destination", "to") or "Not detected"
        destination_status = _destination_status(city)
        fixes = _suggested_fixes(row, flags, destination_status)
        status = _status(confidence, flags, destination_status)
        reviews.append(
            StructuredInputRowReview(
                row_number=index,
                day=_text(row, "day") or "Unassigned",
                service_type=get_row_type(row) or "Other",
                city=city,
                title=_row_title(row),
                confidence=confidence,
                confidence_label=_confidence_label(confidence),
                status=status,
                review_priority=_review_priority(status, confidence),
                destination_status=destination_status,
                primary_fix=_primary_fix(fixes),
                next_action=_next_action(row, status, fixes, destination_status),
                flags=flags,
                missing_fields=_missing_fields(flags),
                suggested_fixes=fixes,
            )
        )
    return tuple(reviews)



def _canonical_destination_name(value: str) -> str:
    record = destination_for_alias(value)
    return record.name if record else str(value or "").strip()


def _correction_field_updates(row: Mapping[str, Any]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    declared_type = _text(row, "type")
    effective_type = _text(row, "effective_type")
    if declared_type and effective_type and declared_type != effective_type:
        updates["type"] = effective_type

    for key in ("city", "destination", "route_origin", "route_destination", "from", "to"):
        value = _text(row, key)
        if not value:
            continue
        canonical = _canonical_destination_name(value)
        if canonical and canonical != value and destination_for_alias(value) is not None:
            updates[key] = canonical
    return updates


def build_input_correction_actions(
    rows: Iterable[Mapping[str, Any]] | None,
) -> tuple[StructuredInputCorrectionAction, ...]:
    """Return safe, explicit correction actions for parsed supplier rows.

    These actions are intentionally conservative. They only cover parser-normalized
    row types and registry-backed destination canonicalization; missing commercial
    facts still require human review.
    """

    actions: list[StructuredInputCorrectionAction] = []
    for index, row in enumerate(_rows(rows), start=1):
        updates = _correction_field_updates(row)
        if not updates:
            continue
        labels: list[str] = []
        declared_type = _text(row, "type")
        effective_type = _text(row, "effective_type")
        if declared_type and effective_type and declared_type != effective_type:
            labels.append(f"type {declared_type} → {effective_type}")
        destination_updates = [key for key in updates if key != "type"]
        if destination_updates:
            labels.append("destination spelling")
        action_label = "Accept parser fix: " + ", ".join(labels)
        actions.append(
            StructuredInputCorrectionAction(
                row_number=index,
                action_type="safe_parser_fix",
                action_label=action_label,
                safe_auto_apply=True,
                field_updates=updates,
                reason="Parser-normalized row type or destination alias can be accepted safely.",
            )
        )
    return tuple(actions)


def apply_input_correction_actions(
    rows: Iterable[Mapping[str, Any]] | None,
    actions: Iterable[StructuredInputCorrectionAction | Mapping[str, Any]] | None = None,
    *,
    row_numbers: Iterable[int] | None = None,
) -> tuple[list[dict[str, Any]], tuple[StructuredInputCorrectionAction, ...]]:
    """Apply selected safe input corrections to parsed rows.

    Returns a corrected row list plus the actions that were actually applied.
    """

    normalized_rows = _rows(rows)
    available_actions = tuple(
        action if isinstance(action, StructuredInputCorrectionAction) else StructuredInputCorrectionAction(**dict(action))
        for action in (actions or build_input_correction_actions(normalized_rows))
    )
    selected = set(int(number) for number in row_numbers) if row_numbers is not None else None
    applied: list[StructuredInputCorrectionAction] = []
    by_row = {action.row_number: action for action in available_actions if action.safe_auto_apply}
    for index, row in enumerate(normalized_rows, start=1):
        if selected is not None and index not in selected:
            continue
        action = by_row.get(index)
        if not action:
            continue
        for key, value in action.field_updates.items():
            row[key] = value
        row.setdefault("accepted_input_corrections", [])
        if isinstance(row["accepted_input_corrections"], list):
            row["accepted_input_corrections"].append(action.action_label)
        applied.append(action)
    return normalized_rows, tuple(applied)

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
        f"Acceptable parser fixes: {len(review.correction_actions)}",
        f"Issues: {review.critical_issue_count} critical / {review.review_issue_count} review / {review.issue_count} total",
    ]
    if review.review_flags:
        flags = ", ".join(f"{label}: {count}" for label, count in review.review_flags.items())
        lines.append(f"Review flags: {flags}")
    blockers = [row for row in review.row_reviews if row.review_priority == "Blocker"]
    needs_review = [row for row in review.row_reviews if row.review_priority == "Review"]
    if review.correction_actions:
        lines.append("Safe parser fixes ready")
        for action in review.correction_actions[:5]:
            lines.append(f"- Row {action.row_number}: {action.action_label}")
    if blockers:
        lines.append("Correction queue: blockers first")
        for row in blockers[:5]:
            lines.append(f"- Row {row.row_number} [{row.next_action}] {row.day} · {row.service_type}: {row.primary_fix}")
    if needs_review:
        lines.append("Review queue: confirm before polishing")
        for row in needs_review[:5]:
            lines.append(f"- Row {row.row_number} [{row.next_action}] {row.day} · {row.service_type}: {row.primary_fix}")
    for issue in review.issues[:12]:
        prefix = f"{issue.day}: " if issue.day else ""
        lines.append(f"- [{issue.severity}] {prefix}{issue.message}")
    return "\n".join(lines)

"""Actionable itinerary health checks used by review and export screens.

This module is deliberately presentation-free.  It turns the parsed row model
into a small set of consultant-facing issues that can be shown before styling,
picture review, or PDF export.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from itinerary_generation.common import group_rows_by_day
from itinerary_generation.day_grouping_utils import get_day_number
from itinerary_generation.row_filters import get_row_type, is_optional_row

CRITICAL = "critical"
REVIEW = "review"
INFO = "info"

_CONTENT_TYPES = {
    "Activity",
    "Cruise",
    "Ferry",
    "Flight",
    "Hotel",
    "Rental Car",
    "Self Drive",
    "Train",
    "Transfer",
}
_TRANSFER_TYPES = {"Transfer", "Flight", "Train", "Ferry", "Cruise", "Rental Car", "Self Drive"}


@dataclass(frozen=True)
class ItineraryHealthIssue:
    """One actionable issue in the parsed itinerary model."""

    code: str
    severity: str
    message: str
    day: str = ""
    city: str = ""
    row_type: str = ""
    source: str = "parsed_rows"

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ItineraryHealthSummary:
    """Small aggregate used by UI cards and export preflight."""

    critical: int
    review: int
    info: int
    total: int

    @property
    def status_label(self) -> str:
        if self.critical:
            return "Needs review"
        if self.review:
            return "Review"
        return "Clear"


def _rows(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    return [dict(row) for row in rows or [] if isinstance(row, Mapping)]


def _text(row: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = str(row.get(key, "") or "").strip()
        if value:
            return value
    return ""


def _day(row: Mapping[str, Any]) -> str:
    return _text(row, "day", "day_label")


def _city(row: Mapping[str, Any]) -> str:
    return _text(row, "city", "destination", "location")


def _is_main_row(row: Mapping[str, Any]) -> bool:
    row_type = get_row_type(row)
    return row_type in _CONTENT_TYPES and not is_optional_row(row)


def _has_title(row: Mapping[str, Any]) -> bool:
    return bool(_text(row, "title", "original_title", "activity_title", "hotel_name", "name"))


def _has_hotel_name(row: Mapping[str, Any]) -> bool:
    return bool(_text(row, "hotel_name", "hotel", "accommodation", "title", "name"))


def _has_transfer_endpoint(row: Mapping[str, Any], keys: tuple[str, ...]) -> bool:
    return bool(_text(row, *keys))


def _issue(code: str, severity: str, message: str, row: Mapping[str, Any] | None = None) -> ItineraryHealthIssue:
    row = row or {}
    return ItineraryHealthIssue(
        code=code,
        severity=severity,
        message=message,
        day=_day(row),
        city=_city(row),
        row_type=get_row_type(row) if row else "",
    )


def build_itinerary_health_issues(
    parsed_rows: Iterable[Mapping[str, Any]] | None,
    *,
    parser_diagnostics: Iterable[Mapping[str, Any]] | None = None,
) -> tuple[ItineraryHealthIssue, ...]:
    """Return deterministic, actionable health issues for the parsed model."""

    rows = _rows(parsed_rows)
    issues: list[ItineraryHealthIssue] = []
    main_rows = [row for row in rows if _is_main_row(row)]

    for row in main_rows:
        row_type = get_row_type(row)
        day = _day(row) or "Unknown day"
        city = _city(row)
        if row_type == "Hotel" and not _has_hotel_name(row):
            issues.append(_issue(
                "missing_hotel_name",
                CRITICAL,
                f"{day}: hotel row is missing a hotel name.",
                row,
            ))
        if row_type in _TRANSFER_TYPES:
            has_origin = _has_transfer_endpoint(row, ("origin", "from", "from_city", "pickup", "pickup_place", "start_location"))
            has_destination = _has_transfer_endpoint(row, ("destination", "to", "to_city", "dropoff", "dropoff_place", "end_location"))
            has_details = bool(_text(row, "details", "description", "route", "title", "original_title"))
            if not has_details and not (has_origin and has_destination):
                issues.append(_issue(
                    "missing_transfer_route",
                    REVIEW,
                    f"{day}: {row_type} needs clearer origin/destination details.",
                    row,
                ))
        if row_type != "Hotel" and not city and row_type in {"Activity", "Transfer", "Train", "Cruise", "Ferry"}:
            issues.append(_issue(
                "missing_city",
                REVIEW,
                f"{day}: {row_type} is missing a city or area.",
                row,
            ))

    grouped = group_rows_by_day(main_rows)
    for day, day_rows in grouped.items():
        counts = Counter(get_row_type(row) for row in day_rows)
        total = sum(1 for row in day_rows if get_row_type(row) in _CONTENT_TYPES)
        if total >= 7 or counts.get("Activity", 0) >= 4:
            issues.append(ItineraryHealthIssue(
                code="busy_day_pdf_risk",
                severity=REVIEW,
                message=f"{day}: many services may overflow one A4 page; review layout before export.",
                day=str(day),
                row_type="Day",
                source="layout_preflight",
            ))

    day_numbers = sorted({get_day_number(row.get("day", "")) for row in main_rows if get_day_number(row.get("day", ""))})
    if day_numbers:
        expected = set(range(day_numbers[0], day_numbers[-1] + 1))
        missing = sorted(expected - set(day_numbers))
        if missing:
            issues.append(ItineraryHealthIssue(
                code="missing_day_numbers",
                severity=REVIEW,
                message=f"Generated structure skips day number(s): {', '.join(str(day) for day in missing)}.",
                source="day_sequence",
            ))

    for diagnostic in parser_diagnostics or []:
        message = str(diagnostic.get("message", "") if isinstance(diagnostic, Mapping) else diagnostic).strip()
        category = str(diagnostic.get("category", "parser") if isinstance(diagnostic, Mapping) else "parser").strip()
        if message:
            issues.append(ItineraryHealthIssue(
                code=f"parser_{category or 'notice'}",
                severity=INFO,
                message=f"Parser notice: {message}",
                source="parser_diagnostics",
            ))

    seen: set[tuple[str, str, str, str]] = set()
    unique: list[ItineraryHealthIssue] = []
    for issue in issues:
        key = (issue.code, issue.day, issue.city, issue.message)
        if key in seen:
            continue
        seen.add(key)
        unique.append(issue)
    return tuple(unique)


def summarize_itinerary_health_issues(issues: Iterable[ItineraryHealthIssue]) -> ItineraryHealthSummary:
    counts = Counter(issue.severity for issue in issues)
    total = sum(counts.values())
    return ItineraryHealthSummary(
        critical=counts.get(CRITICAL, 0),
        review=counts.get(REVIEW, 0),
        info=counts.get(INFO, 0),
        total=total,
    )

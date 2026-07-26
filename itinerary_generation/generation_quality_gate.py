"""Generation-input quality gate for parsed itinerary rows."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from itinerary_generation.day_grouping_utils import get_day_number
from itinerary_generation.row_filters import get_commercial_status, get_row_type, is_optional_row
from itinerary_generation.quality_row_selection import (
    IMPORTANT_ROW_TYPES,
    as_quality_rows,
    select_important_rows,
)
from itinerary_generation.row_sequence import ordered_cities
from itinerary_generation.itinerary_continuity import evaluate_itinerary_continuity
from itinerary_generation.quality_gate_patterns import SUSPICIOUS_AM_PM_TIME_RANGE_RE

BLOCKING = "error"
WARNING = "warning"


@dataclass(frozen=True)
class ItineraryValidationIssue:
    """A single validation finding for the parsed itinerary model."""

    severity: str
    code: str
    message: str
    context: str = ""


@dataclass(frozen=True)
class ItineraryQualitySnapshot:
    """Small deterministic summary used by safety checks and tests."""

    row_count: int
    important_count: int
    main_count: int
    optional_count: int
    self_arranged_count: int
    excluded_count: int
    input_max_day: int
    main_max_day: int
    optional_max_day: int
    input_cities: tuple[str, ...] = field(default_factory=tuple)
    main_cities: tuple[str, ...] = field(default_factory=tuple)
    optional_cities: tuple[str, ...] = field(default_factory=tuple)

    @property
    def optional_ratio(self) -> float:
        if not self.important_count:
            return 0.0
        return self.optional_count / self.important_count


@dataclass(frozen=True)
class ItineraryQualityGateReport:
    """Validation report returned by the structural quality gate."""

    snapshot: ItineraryQualitySnapshot
    issues: tuple[ItineraryValidationIssue, ...] = field(default_factory=tuple)

    @property
    def blocking_issues(self) -> tuple[ItineraryValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == BLOCKING)

    @property
    def warnings(self) -> tuple[ItineraryValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == WARNING)

    @property
    def is_blocked(self) -> bool:
        return bool(self.blocking_issues)


def _max_day(rows: Iterable[dict]) -> int:
    values = [get_day_number(row.get("day", "")) for row in rows]
    return max(values) if values else 0



def build_quality_snapshot(parsed_rows) -> ItineraryQualitySnapshot:
    """Return stable row/day/status metrics for the parsed itinerary."""
    rows = as_quality_rows(parsed_rows)
    important_rows = select_important_rows(rows)
    main_rows = [row for row in important_rows if not is_optional_row(row)]
    optional_rows = [row for row in important_rows if is_optional_row(row)]
    self_arranged_rows = [row for row in important_rows if get_commercial_status(row) == "self_arranged"]
    excluded_rows = [row for row in important_rows if get_commercial_status(row) == "excluded"]

    return ItineraryQualitySnapshot(
        row_count=len(rows),
        important_count=len(important_rows),
        main_count=len(main_rows),
        optional_count=len(optional_rows),
        self_arranged_count=len(self_arranged_rows),
        excluded_count=len(excluded_rows),
        input_max_day=_max_day(important_rows),
        main_max_day=_max_day(main_rows),
        optional_max_day=_max_day(optional_rows),
        input_cities=ordered_cities(important_rows),
        main_cities=ordered_cities(main_rows),
        optional_cities=ordered_cities(optional_rows),
    )


def _validate_snapshot(snapshot: ItineraryQualitySnapshot) -> list[ItineraryValidationIssue]:
    issues: list[ItineraryValidationIssue] = []

    if snapshot.important_count and not snapshot.main_count:
        issues.append(
            ItineraryValidationIssue(
                BLOCKING,
                "no_main_itinerary_rows",
                "No included itinerary rows were available after parsing. Review row types and optional/add-on classification.",
            )
        )
        return issues

    if snapshot.input_max_day and snapshot.main_max_day and snapshot.input_max_day - snapshot.main_max_day >= 2:
        if snapshot.optional_max_day > snapshot.main_max_day:
            issues.append(
                ItineraryValidationIssue(
                    BLOCKING,
                    "main_itinerary_truncated_by_optional_rows",
                    (
                        f"Input reaches Day {snapshot.input_max_day}, but the included itinerary only reaches Day {snapshot.main_max_day}. "
                        "Later rows were classified as optional. Review optional/add-on classification before generating the PDF."
                    ),
                    context=f"optional_max_day={snapshot.optional_max_day}",
                )
            )

    if snapshot.optional_count and snapshot.optional_ratio >= 0.45 and snapshot.optional_max_day > snapshot.main_max_day:
        issues.append(
            ItineraryValidationIssue(
                BLOCKING,
                "too_many_late_optional_rows",
                (
                    f"{snapshot.optional_count} of {snapshot.important_count} important rows are optional and optional rows extend beyond the included itinerary. "
                    "This usually means optional status leaked from supplier text."
                ),
                context=f"optional_ratio={snapshot.optional_ratio:.2f}",
            )
        )

    if snapshot.input_cities and snapshot.main_cities:
        missing_main_cities = [city for city in snapshot.input_cities if city not in snapshot.main_cities and city not in snapshot.optional_cities]
        if missing_main_cities:
            issues.append(
                ItineraryValidationIssue(
                    WARNING,
                    "unclassified_destination_rows",
                    "Some destination rows were not classified into included or optional itinerary buckets: "
                    + ", ".join(missing_main_cities)
                    + ".",
                )
            )

    if snapshot.optional_count >= 4 and snapshot.optional_ratio >= 0.30:
        issues.append(
            ItineraryValidationIssue(
                WARNING,
                "large_optional_share",
                (
                    f"{snapshot.optional_count} of {snapshot.important_count} important rows are optional. "
                    "Check that optional add-ons are intentional and not leaked from supplier text."
                ),
                context=f"optional_ratio={snapshot.optional_ratio:.2f}",
            )
        )

    return issues



def _source_fidelity_issues(rows: Iterable[dict]) -> list[ItineraryValidationIssue]:
    issues: list[ItineraryValidationIssue] = []
    typo_re = re.compile(r"\b(?:Meeteing|Funicluar|Funicual|Profesional|athmosphere|Kristinsand|Crusie)\b", flags=re.IGNORECASE)
    for row in rows:
        row_type = get_row_type(row)
        context = " | ".join(str(row.get(key, "")) for key in ("day", "type", "city", "title") if row.get(key))
        if row_type == "Hotel" and row.get("hotel_night_mismatch"):
            issues.append(
                ItineraryValidationIssue(
                    WARNING,
                    "hotel_nights_date_mismatch",
                    "Hotel night count in the source text conflicts with the start/end dates; the date-derived stay length was used.",
                    context=context or str(row.get("hotel_night_mismatch", "")),
                )
            )
        raw_text = " ".join(str(row.get(key, "")) for key in ("raw", "details", "original_title", "title"))
        if SUSPICIOUS_AM_PM_TIME_RANGE_RE.search(raw_text):
            issues.append(
                ItineraryValidationIssue(
                    WARNING,
                    "suspicious_am_pm_time_range",
                    "A source time range crosses AM to PM and may be a supplier typo. Review before sending to the client.",
                    context=context,
                )
            )
        # Known typo corrections are intentionally silent in the default review UI.
        # They are deterministic cleanup events, not client-risk issues. Keep
        # parser diagnostics/advanced logs for audit trails instead of showing
        # repetitive yellow review cards to the user.
        if typo_re.search(raw_text):
            continue
    return issues

def evaluate_itinerary_quality(parsed_rows) -> ItineraryQualityGateReport:
    """Run the structural itinerary safety gate."""
    rows = as_quality_rows(parsed_rows)
    snapshot = build_quality_snapshot(rows)
    continuity_issues = [
        ItineraryValidationIssue(
            finding.severity,
            finding.code,
            finding.message,
            context=finding.context,
        )
        for finding in evaluate_itinerary_continuity(rows)
    ]
    issues = tuple(_validate_snapshot(snapshot) + _source_fidelity_issues(rows) + continuity_issues)
    return ItineraryQualityGateReport(snapshot=snapshot, issues=issues)


def validate_itinerary_integrity(parsed_rows) -> list[ItineraryValidationIssue]:
    """Compatibility wrapper returning just the validation issues."""
    return list(evaluate_itinerary_quality(parsed_rows).issues)


def blocking_validation_messages(parsed_rows) -> list[str]:
    return [issue.message for issue in evaluate_itinerary_quality(parsed_rows).blocking_issues]

__all__ = [
    "IMPORTANT_ROW_TYPES",
    "BLOCKING",
    "WARNING",
    "ItineraryValidationIssue",
    "ItineraryQualitySnapshot",
    "ItineraryQualityGateReport",
    "_max_day",
    "build_quality_snapshot",
    "_validate_snapshot",
    "_source_fidelity_issues",
    "evaluate_itinerary_quality",
    "validate_itinerary_integrity",
    "blocking_validation_messages",
]

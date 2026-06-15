"""Diagnostic itinerary health report helpers.

The health report is intentionally operational rather than client-facing.  It
summarizes the parsed/canonical row model so consultants and developers can
spot truncation, optional leakage, missing commercial classification, and route
coverage issues before exporting a PDF.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from itinerary_generation.common_constants import TRANSPORT_TYPES
from itinerary_generation.day_grouping_utils import get_day_number
from itinerary_generation.quality_gate import (
    IMPORTANT_ROW_TYPES,
    ItineraryQualityGateReport,
    build_quality_snapshot,
    evaluate_itinerary_quality,
)
from itinerary_generation.row_filters import get_commercial_status, get_row_type, is_optional_row
from itinerary_generation.row_sequence import ordered_cities
from itinerary_generation.structured_builder import build_itinerary_document


@dataclass(frozen=True)
class ItineraryHealthReport:
    """Stable diagnostic summary of a parsed itinerary model."""

    input_days: int
    generated_days: int
    included_rows: int
    optional_rows: int
    self_arranged_rows: int
    excluded_rows: int
    hotels_found: int
    activities_found: int
    transfers_found: int
    route: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def route_text(self) -> str:
        return " → ".join(self.route) if self.route else "Not detected"

    @property
    def warnings_text(self) -> str:
        return "none" if not self.warnings else "; ".join(self.warnings)

    @property
    def status(self) -> str:
        if any("blocked" in warning.lower() or "input reaches" in warning.lower() for warning in self.warnings):
            return "Needs review"
        if self.warnings:
            return "Review"
        return "Clear"


def _as_rows(rows: Iterable[dict] | None) -> list[dict]:
    return [row for row in rows or [] if isinstance(row, dict)]


def _is_important_row(row: dict) -> bool:
    row_type = get_row_type(row)
    raw_type = row.get("type", "")
    return row_type in IMPORTANT_ROW_TYPES or raw_type in IMPORTANT_ROW_TYPES


def _important_rows(rows: Iterable[dict]) -> list[dict]:
    return [row for row in rows if _is_important_row(row)]


def _max_day(rows: Iterable[dict]) -> int:
    day_numbers = [get_day_number(row.get("day", "")) for row in rows]
    return max(day_numbers) if day_numbers else 0



def _validation_warnings(report: ItineraryQualityGateReport) -> list[str]:
    warnings: list[str] = []
    for issue in report.blocking_issues:
        warnings.append(f"Blocked: {issue.message}")
    for issue in report.warnings:
        warnings.append(issue.message)
    return warnings


def build_itinerary_health_report(
    parsed_rows: Iterable[dict] | None,
    validation_report: ItineraryQualityGateReport | None = None,
    parser_diagnostics: Iterable[dict] | None = None,
) -> ItineraryHealthReport:
    """Build a deterministic diagnostic report from parsed itinerary rows."""

    rows = _as_rows(parsed_rows)
    important_rows = _important_rows(rows)
    validation_report = validation_report or evaluate_itinerary_quality(rows)
    snapshot = build_quality_snapshot(rows)

    included_rows = [
        row
        for row in important_rows
        if get_commercial_status(row) == "included" and not is_optional_row(row)
    ]
    optional_rows = [row for row in important_rows if get_commercial_status(row) == "optional" or is_optional_row(row)]
    self_arranged_rows = [row for row in important_rows if get_commercial_status(row) == "self_arranged"]
    excluded_rows = [row for row in important_rows if get_commercial_status(row) == "excluded"]

    non_optional_rows = [row for row in important_rows if not is_optional_row(row)]
    commercial_main_rows = [row for row in non_optional_rows if get_commercial_status(row) != "excluded"]

    hotel_rows = [row for row in included_rows if get_row_type(row) == "Hotel"]
    activity_rows = [row for row in included_rows if get_row_type(row) == "Activity"]
    transport_types = set(TRANSPORT_TYPES) | {"Transfer"}
    transfer_rows = [row for row in non_optional_rows if get_row_type(row) in transport_types]

    warnings = _validation_warnings(validation_report)
    if snapshot.input_max_day and snapshot.main_max_day and snapshot.main_max_day < snapshot.input_max_day:
        warnings.append(
            f"Input reaches Day {snapshot.input_max_day}, but the generated non-optional itinerary reaches Day {snapshot.main_max_day}."
        )

    parser_diagnostic_count = len(list(parser_diagnostics or []))
    if parser_diagnostic_count:
        warnings.append(f"Parser diagnostics recorded: {parser_diagnostic_count} notice(s).")

    structured_document = build_itinerary_document(rows)
    for model_warning in structured_document.warnings:
        prefix = "Structured model"
        severity = str(model_warning.severity or "warning").title()
        warnings.append(f"{prefix} {severity}: {model_warning.message}")

    return ItineraryHealthReport(
        input_days=snapshot.input_max_day,
        generated_days=snapshot.main_max_day,
        included_rows=len(included_rows),
        optional_rows=len(optional_rows),
        self_arranged_rows=len(self_arranged_rows),
        excluded_rows=len(excluded_rows),
        hotels_found=len(hotel_rows),
        activities_found=len(activity_rows),
        transfers_found=len(transfer_rows),
        route=ordered_cities(commercial_main_rows) or snapshot.main_cities or snapshot.input_cities,
        warnings=tuple(dict.fromkeys(warnings)),
    )


def format_itinerary_health_report(report: ItineraryHealthReport) -> str:
    """Return a copy-friendly plain-text health report."""

    lines = [
        "Itinerary Health Report",
        f"Status: {report.status}",
        f"Input days: {report.input_days}",
        f"Generated days: {report.generated_days}",
        f"Included rows: {report.included_rows}",
        f"Optional rows: {report.optional_rows}",
        f"Self-arranged rows: {report.self_arranged_rows}",
        f"Excluded rows: {report.excluded_rows}",
        f"Hotels found: {report.hotels_found}",
        f"Activities found: {report.activities_found}",
        f"Transfers found: {report.transfers_found}",
        f"Route: {report.route_text}",
        f"Warnings: {report.warnings_text}",
    ]
    return "\n".join(lines)

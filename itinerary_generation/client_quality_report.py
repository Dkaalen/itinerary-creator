"""Immutable report model for client-output quality validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from itinerary_generation.advisor_quality import AdvisorQualityAssessment, assess_advisor_readiness
from itinerary_generation.generation_quality_gate import BLOCKING, WARNING, ItineraryValidationIssue


@dataclass(frozen=True)
class ClientOutputQualityGateReport:
    """One deduplicated issue set and its precomputed advisor assessment."""

    issues: tuple[ItineraryValidationIssue, ...] = field(default_factory=tuple)
    advisor_assessment: AdvisorQualityAssessment = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "advisor_assessment", assess_advisor_readiness(self.issues))

    @property
    def blocking_issues(self) -> tuple[ItineraryValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == BLOCKING)

    @property
    def warnings(self) -> tuple[ItineraryValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == WARNING)

    @property
    def is_blocked(self) -> bool:
        return bool(self.blocking_issues)

    @property
    def advisor_rating(self) -> str:
        return self.advisor_assessment.rating


def build_client_output_quality_report(
    issues: Iterable[ItineraryValidationIssue],
) -> ClientOutputQualityGateReport:
    """Build one deterministic report while collapsing overlapping findings."""

    unique: list[ItineraryValidationIssue] = []
    seen: set[tuple[str, str, str, str]] = set()
    for issue in issues:
        key = (issue.severity, issue.code, issue.message, issue.context)
        if key in seen:
            continue
        unique.append(issue)
        seen.add(key)
    return ClientOutputQualityGateReport(tuple(unique))


def extend_client_output_quality_report(
    report: ClientOutputQualityGateReport,
    issues: Iterable[ItineraryValidationIssue],
) -> ClientOutputQualityGateReport:
    """Return a new report with additional findings without rerunning base rules."""

    return build_client_output_quality_report((*report.issues, *tuple(issues)))


__all__ = [
    "ClientOutputQualityGateReport",
    "build_client_output_quality_report",
    "extend_client_output_quality_report",
]

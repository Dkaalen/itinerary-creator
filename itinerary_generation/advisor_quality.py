"""Advisor-grade sendability classification for generated client output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from itinerary_generation.generation_quality_gate import BLOCKING, ItineraryValidationIssue

READY = "Ready"
MINOR_EDIT = "Minor edit"
MAJOR_EDIT = "Major edit"
UNUSABLE = "Unusable"

_MAJOR_CODES = {
    "serious_copy_repetition",
    "geographic_uncertainty",
    "seasonal_uncertainty",
    "product_fidelity_review",
    "multiple_missing_commercial_details",
}
_MINOR_PREFIXES = ("missing_confirmed_", "weak_generic_fallback")


@dataclass(frozen=True)
class AdvisorQualityAssessment:
    rating: str
    reasons: tuple[str, ...] = ()
    issue_codes: tuple[str, ...] = ()

    @property
    def is_ready(self) -> bool:
        return self.rating == READY

    @property
    def is_blocked(self) -> bool:
        return self.rating == UNUSABLE


def assess_advisor_readiness(issues: Iterable[ItineraryValidationIssue]) -> AdvisorQualityAssessment:
    findings = tuple(issues or ())
    if not findings:
        return AdvisorQualityAssessment(READY)

    blocking = tuple(issue for issue in findings if issue.severity == BLOCKING)
    if blocking:
        return AdvisorQualityAssessment(
            UNUSABLE,
            tuple(dict.fromkeys(issue.message for issue in blocking)),
            tuple(dict.fromkeys(issue.code for issue in blocking)),
        )

    codes = tuple(dict.fromkeys(issue.code for issue in findings))
    missing_details = [code for code in codes if code.startswith("missing_confirmed_")]
    major = [issue for issue in findings if issue.code in _MAJOR_CODES]
    if len(missing_details) >= 2:
        major.append(
            ItineraryValidationIssue(
                "warning",
                "multiple_missing_commercial_details",
                "Several confirmed product details are missing from the client output.",
            )
        )
    if major:
        return AdvisorQualityAssessment(
            MAJOR_EDIT,
            tuple(dict.fromkeys(issue.message for issue in major)),
            tuple(dict.fromkeys(issue.code for issue in major)),
        )

    minor = [
        issue for issue in findings
        if issue.code.startswith(_MINOR_PREFIXES) or issue.severity == "warning"
    ]
    if minor:
        return AdvisorQualityAssessment(
            MINOR_EDIT,
            tuple(dict.fromkeys(issue.message for issue in minor)),
            tuple(dict.fromkeys(issue.code for issue in minor)),
        )
    return AdvisorQualityAssessment(READY)


__all__ = [
    "AdvisorQualityAssessment",
    "MAJOR_EDIT",
    "MINOR_EDIT",
    "READY",
    "UNUSABLE",
    "assess_advisor_readiness",
]

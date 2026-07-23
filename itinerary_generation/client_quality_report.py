"""Report model for client-output quality validation."""

from dataclasses import dataclass, field
from itinerary_generation.generation_quality_gate import BLOCKING, WARNING, ItineraryValidationIssue
from itinerary_generation.advisor_quality import AdvisorQualityAssessment, assess_advisor_readiness


@dataclass(frozen=True)
class ClientOutputQualityGateReport:
    issues: tuple[ItineraryValidationIssue, ...] = field(default_factory=tuple)

    @property
    def blocking_issues(self): return tuple(issue for issue in self.issues if issue.severity == BLOCKING)

    @property
    def warnings(self): return tuple(issue for issue in self.issues if issue.severity == WARNING)

    @property
    def is_blocked(self) -> bool: return bool(self.blocking_issues)

    @property
    def advisor_assessment(self) -> AdvisorQualityAssessment:
        return assess_advisor_readiness(self.issues)

    @property
    def advisor_rating(self) -> str:
        return self.advisor_assessment.rating

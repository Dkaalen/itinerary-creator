"""Structured input-review dataclasses."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from itinerary_generation.itinerary_health_checks import ItineraryHealthIssue


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

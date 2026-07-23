"""Data models for real-output QA reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from scripts.real_excel_fixture_bank import ExcelFixtureCandidate

@dataclass(frozen=True)
class TextSegment:
    """A small client-facing text unit with enough location data for reports."""

    location: str
    kind: str
    text: str
    day: str = ""


@dataclass(frozen=True)
class OutputTextIssue:
    code: str
    severity: str
    message: str
    location: str = ""
    excerpt: str = ""


@dataclass(frozen=True)
class OutputTextScore:
    score: int
    error_count: int
    warning_count: int
    issues: tuple[OutputTextIssue, ...] = ()
    advisor_rating: str = "Ready"
    advisor_reasons: tuple[str, ...] = ()

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def ok(self) -> bool:
        return self.error_count == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issue_count": self.issue_count,
            "ok": self.ok,
            "advisor_rating": self.advisor_rating,
            "advisor_reasons": list(self.advisor_reasons),
            "issues": [asdict(issue) for issue in self.issues],
        }


@dataclass(frozen=True)
class DayOutputSnapshot:
    day: str
    title: str
    city: str
    intro: str
    source_rows: tuple[str, ...] = ()
    transport: tuple[str, ...] = ()
    accommodation: tuple[str, ...] = ()
    activities: tuple[str, ...] = ()
    leisure: tuple[str, ...] = ()
    optional_experiences: tuple[str, ...] = ()
    other_blocks: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    decision_labels: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CandidateOutputReview:
    fixture: dict[str, Any]
    parsed_row_count: int
    rendered_day_count: int
    trip_title: str
    trip_subtitle: str
    route: str
    journey_title: str = ""
    journey_arc: tuple[dict[str, str], ...] = ()
    days: tuple[DayOutputSnapshot, ...] = ()
    included: tuple[str, ...] = ()
    optional_addons: tuple[str, ...] = ()
    not_included: tuple[str, ...] = ()
    render_warnings: tuple[str, ...] = ()
    score: OutputTextScore = field(default_factory=lambda: OutputTextScore(score=0, error_count=1, warning_count=0))

    @property
    def ok(self) -> bool:
        return self.score.ok

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["score"] = self.score.to_dict()
        data["ok"] = self.ok
        return data


@dataclass(frozen=True)
class CandidateRenderResult:
    candidate: ExcelFixtureCandidate
    rows: tuple[dict[str, Any], ...]
    grouped_rows: dict[str, list[dict[str, Any]]]
    context: Any


class CandidateRenderError(RuntimeError):
    """Raised when a fixture cannot be parsed or rendered for output review."""



__all__ = [
    "CandidateOutputReview",
    "CandidateRenderError",
    "CandidateRenderResult",
    "DayOutputSnapshot",
    "OutputTextIssue",
    "OutputTextScore",
    "TextSegment",
]

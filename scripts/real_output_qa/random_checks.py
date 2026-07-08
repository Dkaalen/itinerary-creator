"""Random seeded quality-check report assembly for real Excel fixtures."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from scripts.real_excel_fixture_bank import DEFAULT_MANIFEST, ExcelFixtureCandidate, build_candidate_index, build_index_summary, select_random_candidates
from scripts.real_output_qa.models import OutputTextIssue
from scripts.real_output_qa.rendering import render_candidate_review


@dataclass(frozen=True)
class RandomQualityIssue:
    code: str
    severity: str
    message: str
    excerpt: str = ""
    location: str = ""


@dataclass(frozen=True)
class CandidateReview:
    fixture: dict[str, Any]
    parsed_row_count: int
    rendered_day_count: int
    trip_title: str
    trip_subtitle: str
    score: int
    error_count: int
    warning_count: int
    issue_count: int
    issues: tuple[RandomQualityIssue, ...]

    @property
    def ok(self) -> bool:
        return self.error_count == 0


def from_score_issue(issue: OutputTextIssue) -> RandomQualityIssue:
    """Convert a shared score issue into the random-check report shape."""

    return RandomQualityIssue(
        code=issue.code,
        severity=issue.severity,
        message=issue.message,
        excerpt=issue.excerpt,
        location=issue.location,
    )


def review_candidate(candidate: ExcelFixtureCandidate) -> CandidateReview:
    """Render and score one random-check candidate."""

    review = render_candidate_review(candidate)
    issues = tuple(from_score_issue(issue) for issue in review.score.issues)
    return CandidateReview(
        fixture=review.fixture,
        parsed_row_count=review.parsed_row_count,
        rendered_day_count=review.rendered_day_count,
        trip_title=review.trip_title,
        trip_subtitle=review.trip_subtitle,
        score=review.score.score,
        error_count=review.score.error_count,
        warning_count=review.score.warning_count,
        issue_count=review.score.issue_count,
        issues=issues,
    )


def select_quality_candidates(
    *,
    manifest_path: Path,
    sample_size: int,
    seed: int,
    include_all: bool = False,
    include_workbooks: Iterable[str] = (),
) -> tuple[ExcelFixtureCandidate, ...]:
    """Select real Excel candidates for random quality checks."""

    candidates = build_candidate_index(manifest_path)
    if include_workbooks:
        terms = tuple(term.casefold() for term in include_workbooks)
        candidates = tuple(candidate for candidate in candidates if any(term in candidate.workbook_path.name.casefold() for term in terms))
    return candidates if include_all else select_random_candidates(candidates, sample_size=sample_size, seed=seed)


def build_quality_report_from_candidates(
    candidates: tuple[ExcelFixtureCandidate, ...],
    *,
    seed: int,
    bank_candidates: tuple[ExcelFixtureCandidate, ...],
) -> dict[str, Any]:
    """Score selected candidates and return the CLI JSON payload."""

    reviews = [review_candidate(candidate) for candidate in candidates]
    return {
        "seed": seed,
        "sample_size": len(candidates),
        "selected_fixture_ids": [candidate.fixture_id for candidate in candidates],
        "bank_summary": build_index_summary(bank_candidates),
        "error_count": sum(review.error_count for review in reviews),
        "warning_count": sum(review.warning_count for review in reviews),
        "average_score": round(sum(review.score for review in reviews) / len(reviews), 1) if reviews else 0,
        "reviews": [
            {
                **asdict(review),
                "issues": [asdict(issue) for issue in review.issues],
                "ok": review.ok,
            }
            for review in reviews
        ],
    }


def build_random_quality_report(
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    sample_size: int = 5,
    seed: int = 0,
    include_all: bool = False,
    include_workbooks: Iterable[str] = (),
) -> dict[str, Any]:
    """Build the seeded random quality-check report."""

    bank_candidates = build_candidate_index(manifest_path)
    selected = select_quality_candidates(
        manifest_path=manifest_path,
        sample_size=sample_size,
        seed=seed,
        include_all=include_all,
        include_workbooks=include_workbooks,
    )
    return build_quality_report_from_candidates(selected, seed=seed, bank_candidates=bank_candidates)


# Legacy private alias for compatibility with old test imports.
_from_score_issue = from_score_issue

__all__ = [
    "CandidateReview",
    "RandomQualityIssue",
    "build_quality_report_from_candidates",
    "build_random_quality_report",
    "from_score_issue",
    "review_candidate",
    "select_quality_candidates",
    "_from_score_issue",
]

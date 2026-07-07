"""Randomly run real Excel itinerary fixtures through product-output checks."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.real_excel_fixture_bank import (
    DEFAULT_MANIFEST,
    ExcelFixtureCandidate,
    build_candidate_index,
    build_index_summary,
    select_random_candidates,
    write_candidate_raw_text,
)
from scripts.real_output_text_quality import OutputTextIssue, render_candidate_review


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


def _from_score_issue(issue: OutputTextIssue) -> RandomQualityIssue:
    return RandomQualityIssue(
        code=issue.code,
        severity=issue.severity,
        message=issue.message,
        excerpt=issue.excerpt,
        location=issue.location,
    )


def review_candidate(candidate: ExcelFixtureCandidate) -> CandidateReview:
    review = render_candidate_review(candidate)
    issues = tuple(_from_score_issue(issue) for issue in review.score.issues)
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


def _seed_from_args(seed_arg: str | None) -> int:
    if seed_arg not in (None, "", "random"):
        return int(seed_arg)
    return int.from_bytes(os.urandom(4), "big")


def build_random_quality_report(
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    sample_size: int = 5,
    seed: int = 0,
    include_all: bool = False,
    include_workbooks: Iterable[str] = (),
) -> dict[str, Any]:
    candidates = build_candidate_index(manifest_path)
    if include_workbooks:
        terms = tuple(term.casefold() for term in include_workbooks)
        candidates = tuple(candidate for candidate in candidates if any(term in candidate.workbook_path.name.casefold() for term in terms))
    selected = candidates if include_all else select_random_candidates(candidates, sample_size=sample_size, seed=seed)
    reviews = [review_candidate(candidate) for candidate in selected]
    return {
        "seed": seed,
        "sample_size": len(selected),
        "selected_fixture_ids": [candidate.fixture_id for candidate in selected],
        "bank_summary": build_index_summary(candidates),
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run random real-Excel product-output quality checks.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Path to real Excel fixture manifest.")
    parser.add_argument("--sample-size", type=int, default=5, help="Number of fixture sheets to sample.")
    parser.add_argument("--seed", default="random", help="Integer seed, or 'random' to generate one and print it.")
    parser.add_argument("--all", action="store_true", help="Check all extractable workbook sheets instead of sampling.")
    parser.add_argument("--workbook", action="append", default=[], help="Restrict to workbook filename substring. Can be repeated.")
    parser.add_argument("--write-selected-text", default="", help="Optional directory for extracted selected fixture text files.")
    args = parser.parse_args(argv)

    seed = _seed_from_args(args.seed)
    candidates = build_candidate_index(Path(args.manifest))
    if args.workbook:
        terms = tuple(term.casefold() for term in args.workbook)
        candidates = tuple(candidate for candidate in candidates if any(term in candidate.workbook_path.name.casefold() for term in terms))
    selected = candidates if args.all else select_random_candidates(candidates, sample_size=args.sample_size, seed=seed)
    if args.write_selected_text:
        output_dir = Path(args.write_selected_text)
        for candidate in selected:
            write_candidate_raw_text(candidate, output_dir)

    reviews = [review_candidate(candidate) for candidate in selected]
    report = {
        "seed": seed,
        "sample_size": len(selected),
        "selected_fixture_ids": [candidate.fixture_id for candidate in selected],
        "bank_summary": build_index_summary(candidates),
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
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""JSON score-report assembly for real-output QA."""

from __future__ import annotations

from pathlib import Path

from scripts.real_excel_fixture_bank import DEFAULT_MANIFEST, build_candidate_index, build_index_summary
from scripts.real_output_qa.selection import build_reviews


def build_score_report(
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    sample_size: int = 5,
    seed: int = 0,
    include_all: bool = False,
    include_workbooks=(),
    fixture_ids=(),
) -> dict:
    """Build the deterministic score report used by CLI and QA index tools."""

    reviews = build_reviews(
        manifest_path=manifest_path,
        sample_size=sample_size,
        seed=seed,
        include_all=include_all,
        include_workbooks=include_workbooks,
        fixture_ids=fixture_ids,
    )
    candidates = build_candidate_index(manifest_path)
    return {
        "seed": seed,
        "sample_size": len(reviews),
        "selected_fixture_ids": [review.fixture.get("fixture_id", "") for review in reviews],
        "bank_summary": build_index_summary(candidates),
        "error_count": sum(review.score.error_count for review in reviews),
        "warning_count": sum(review.score.warning_count for review in reviews),
        "average_score": round(sum(review.score.score for review in reviews) / len(reviews), 1) if reviews else 0,
        "reviews": [
            {
                "fixture": review.fixture,
                "parsed_row_count": review.parsed_row_count,
                "rendered_day_count": review.rendered_day_count,
                "trip_title": review.trip_title,
                "trip_subtitle": review.trip_subtitle,
                "route": review.route,
                "score": review.score.to_dict(),
            }
            for review in reviews
        ],
    }


__all__ = ["build_score_report"]

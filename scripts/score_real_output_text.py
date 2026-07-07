"""Run deterministic scoring checks against real Excel itinerary outputs."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.real_excel_fixture_bank import DEFAULT_MANIFEST, build_candidate_index, build_index_summary
from scripts.review_real_output_text import build_reviews


def _seed_from_args(seed_arg: str | None) -> int:
    if seed_arg not in (None, "", "random"):
        return int(seed_arg)
    return int.from_bytes(os.urandom(4), "big")


def build_score_report(
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    sample_size: int = 5,
    seed: int = 0,
    include_all: bool = False,
    include_workbooks=(),
    fixture_ids=(),
) -> dict:
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score real Excel itinerary output text.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Path to real Excel fixture manifest.")
    parser.add_argument("--sample-size", type=int, default=5, help="Number of fixture sheets to sample.")
    parser.add_argument("--seed", default="random", help="Integer seed, or 'random' to generate one and print it.")
    parser.add_argument("--all", action="store_true", help="Score all extractable workbook sheets instead of sampling.")
    parser.add_argument("--workbook", action="append", default=[], help="Restrict to workbook filename substring. Can be repeated.")
    parser.add_argument("--fixture", "--candidate", action="append", default=[], help="Exact fixture id or substring.")
    parser.add_argument("--fail-on-warning", action="store_true", help="Return non-zero when warnings are found.")
    args = parser.parse_args(argv)

    seed = _seed_from_args(args.seed)
    report = build_score_report(
        manifest_path=Path(args.manifest),
        sample_size=args.sample_size,
        seed=seed,
        include_all=args.all,
        include_workbooks=args.workbook,
        fixture_ids=args.fixture,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["error_count"]:
        return 1
    if args.fail_on_warning and report["warning_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

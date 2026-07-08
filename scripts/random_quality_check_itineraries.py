"""Run random quality checks against real Excel itinerary fixtures."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.real_excel_fixture_bank import DEFAULT_MANIFEST, build_candidate_index, write_candidate_raw_text
from scripts.real_output_qa.random_checks import (
    CandidateReview,
    RandomQualityIssue,
    build_quality_report_from_candidates,
    build_random_quality_report,
    review_candidate,
    select_quality_candidates,
)


def _seed_from_args(seed_arg: str | None) -> int:
    if seed_arg not in (None, "", "random"):
        return int(seed_arg)
    return int.from_bytes(os.urandom(4), "big")


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
    manifest_path = Path(args.manifest)
    bank_candidates = build_candidate_index(manifest_path)
    selected = select_quality_candidates(
        manifest_path=manifest_path,
        sample_size=args.sample_size,
        seed=seed,
        include_all=args.all,
        include_workbooks=args.workbook,
    )
    if args.write_selected_text:
        output_dir = Path(args.write_selected_text)
        for candidate in selected:
            write_candidate_raw_text(candidate, output_dir)

    report = build_quality_report_from_candidates(selected, seed=seed, bank_candidates=bank_candidates)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["error_count"] else 0


__all__ = [
    "CandidateReview",
    "RandomQualityIssue",
    "build_random_quality_report",
    "review_candidate",
    "select_quality_candidates",
]


if __name__ == "__main__":
    raise SystemExit(main())

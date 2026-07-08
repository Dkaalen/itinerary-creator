"""Generate readable real-Excel itinerary output review reports."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.real_excel_fixture_bank import DEFAULT_MANIFEST
from scripts.real_output_qa.markdown import DEFAULT_REPORT_DIR, build_markdown_report, write_reports
from scripts.real_output_qa.selection import build_reviews, select_candidates
from scripts.real_output_qa.serialization import reviews_to_json


def _seed_from_args(seed_arg: str | None) -> int:
    if seed_arg not in (None, "", "random"):
        return int(seed_arg)
    return int.from_bytes(os.urandom(4), "big")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate readable text reviews from real Excel itinerary fixtures.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Path to real Excel fixture manifest.")
    parser.add_argument("--sample-size", type=int, default=5, help="Number of fixture sheets to sample.")
    parser.add_argument("--seed", default="random", help="Integer seed, or 'random' to generate one and print it.")
    parser.add_argument("--all", action="store_true", help="Review all extractable workbook sheets instead of sampling.")
    parser.add_argument("--workbook", action="append", default=[], help="Restrict to workbook filename substring. Can be repeated.")
    parser.add_argument("--fixture", "--candidate", action="append", default=[], help="Exact fixture id or substring, e.g. 'Standard-Itinerary-Finland.xlsx::106'.")
    parser.add_argument("--output-dir", default=str(DEFAULT_REPORT_DIR), help="Directory for markdown/json reports.")
    parser.add_argument("--stdout", action="store_true", help="Print markdown to stdout instead of writing files.")
    args = parser.parse_args(argv)

    seed = _seed_from_args(args.seed)
    manifest_path = Path(args.manifest)
    reviews = build_reviews(
        manifest_path=manifest_path,
        sample_size=args.sample_size,
        seed=seed,
        include_all=args.all,
        include_workbooks=args.workbook,
        fixture_ids=args.fixture,
    )
    markdown = build_markdown_report(reviews, seed=seed, sample_size=args.sample_size, manifest_path=manifest_path)
    json_text = reviews_to_json(reviews)
    if args.stdout:
        print(markdown, end="")
    else:
        md_path, json_path = write_reports(markdown, json_text, output_dir=Path(args.output_dir), seed=seed)
        print(f"Seed: {seed}")
        print(f"Wrote {md_path}")
        print(f"Wrote {json_path}")
    total_errors = sum(review.score.error_count for review in reviews)
    return 1 if total_errors else 0


__all__ = [
    "DEFAULT_REPORT_DIR",
    "build_markdown_report",
    "build_reviews",
    "reviews_to_json",
    "select_candidates",
    "write_reports",
]


if __name__ == "__main__":
    raise SystemExit(main())

"""Capture a real-output QA failure as a stable regression fixture."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.review_real_output_text import build_reviews
from scripts.real_excel_fixture_bank import DEFAULT_MANIFEST

DEFAULT_OUTPUT_DIR = ROOT / "tests/fixtures/real_output_regressions"


def _safe_slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_").lower() or "regression"


def build_regression_record(
    *,
    fixture_id: str,
    seed: int,
    name: str,
    expected_behavior: str,
    issue_code: str = "",
    manifest_path: Path = DEFAULT_MANIFEST,
) -> dict[str, Any]:
    reviews = build_reviews(manifest_path=manifest_path, sample_size=1, seed=seed, fixture_ids=[fixture_id])
    if not reviews:
        raise ValueError(f"No fixture matched {fixture_id!r}")
    review = reviews[0]
    score_issues = [asdict(issue) for issue in review.score.issues]
    if issue_code:
        score_issues = [issue for issue in score_issues if issue.get("code") == issue_code] or score_issues
    day_excerpt = []
    for day in review.days[:4]:
        day_excerpt.append({
            "day": day.day,
            "title": day.title,
            "city": day.city,
            "intro": day.intro,
            "transport": list(day.transport[:3]),
            "activities": list(day.activities[:3]),
            "leisure": list(day.leisure[:2]),
            "optional_experiences": list(day.optional_experiences[:2]),
        })
    return {
        "name": name,
        "fixture_id": review.fixture.get("fixture_id", fixture_id),
        "seed": seed,
        "issue_code": issue_code,
        "expected_behavior": expected_behavior,
        "score": review.score.to_dict(),
        "captured_issues": score_issues[:8],
        "trip_title": review.trip_title,
        "trip_subtitle": review.trip_subtitle,
        "route": review.route,
        "day_excerpt": day_excerpt,
    }


def write_regression_record(record: dict[str, Any], output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    fixture_slug = _safe_slug(str(record.get("fixture_id", "fixture"))).replace("xlsx__", "xlsx_")
    name_slug = _safe_slug(str(record.get("name", "regression")))
    path = output_dir / f"{name_slug}__{fixture_slug}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Promote one real-output QA case into a regression fixture JSON.")
    parser.add_argument("--fixture", "--candidate", required=True, help="Fixture id, e.g. Standard-Itinerary-Iceland.xlsx::8D RW")
    parser.add_argument("--seed", type=int, default=0, help="Seed that exposed the issue.")
    parser.add_argument("--name", required=True, help="Short regression name.")
    parser.add_argument("--issue-code", default="", help="Issue code to capture/highlight.")
    parser.add_argument("--expected-behavior", required=True, help="Expected product behavior to protect.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args(argv)
    record = build_regression_record(
        fixture_id=args.fixture,
        seed=args.seed,
        name=args.name,
        issue_code=args.issue_code,
        expected_behavior=args.expected_behavior,
        manifest_path=Path(args.manifest),
    )
    path = write_regression_record(record, Path(args.output_dir))
    try:
        display = path.relative_to(ROOT)
    except ValueError:
        display = path
    print(f"Wrote {display}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

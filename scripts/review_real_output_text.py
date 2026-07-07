"""Generate readable real-Excel itinerary output review reports."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.real_excel_fixture_bank import DEFAULT_MANIFEST, build_candidate_index, build_index_summary, select_random_candidates
from scripts.real_output_text_quality import CandidateOutputReview, render_candidate_review, reviews_to_json

DEFAULT_REPORT_DIR = ROOT / "docs/reports/real_output_text_reviews"


def _seed_from_args(seed_arg: str | None) -> int:
    if seed_arg not in (None, "", "random"):
        return int(seed_arg)
    return int.from_bytes(os.urandom(4), "big")


def _clean_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "report"


def select_candidates(
    *,
    manifest_path: Path,
    sample_size: int,
    seed: int,
    include_all: bool = False,
    include_workbooks: Iterable[str] = (),
    fixture_ids: Iterable[str] = (),
):
    candidates = build_candidate_index(manifest_path)
    workbook_terms = tuple(term.casefold() for term in include_workbooks if term)
    fixture_terms = tuple(term.casefold() for term in fixture_ids if term)
    if workbook_terms:
        candidates = tuple(candidate for candidate in candidates if any(term in candidate.workbook_path.name.casefold() for term in workbook_terms))
    if fixture_terms:
        candidates = tuple(
            candidate
            for candidate in candidates
            if any(term == candidate.fixture_id.casefold() or term in candidate.fixture_id.casefold() for term in fixture_terms)
        )
    if fixture_terms or include_all:
        return candidates
    return select_random_candidates(candidates, sample_size=sample_size, seed=seed)


def build_reviews(
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    sample_size: int = 5,
    seed: int = 0,
    include_all: bool = False,
    include_workbooks: Iterable[str] = (),
    fixture_ids: Iterable[str] = (),
) -> tuple[CandidateOutputReview, ...]:
    selected = select_candidates(
        manifest_path=manifest_path,
        sample_size=sample_size,
        seed=seed,
        include_all=include_all,
        include_workbooks=include_workbooks,
        fixture_ids=fixture_ids,
    )
    return tuple(render_candidate_review(candidate) for candidate in selected)


def _bullet_lines(items: Sequence[str], *, limit: int = 8) -> list[str]:
    if not items:
        return ["  - None detected"]
    lines = [f"  - {item}" for item in items[:limit]]
    if len(items) > limit:
        lines.append(f"  - … {len(items) - limit} more")
    return lines


def build_markdown_report(
    reviews: Sequence[CandidateOutputReview],
    *,
    seed: int,
    sample_size: int,
    manifest_path: Path = DEFAULT_MANIFEST,
) -> str:
    candidates = build_candidate_index(manifest_path)
    summary = build_index_summary(candidates)
    total_errors = sum(review.score.error_count for review in reviews)
    total_warnings = sum(review.score.warning_count for review in reviews)
    lines: list[str] = [
        "# Real Output Text Review",
        "",
        f"Seed: `{seed}`",
        f"Requested sample size: `{sample_size}`",
        f"Reviewed candidates: `{len(reviews)}`",
        f"Fixture bank: `{summary['workbook_count']}` workbooks, `{summary['candidate_count']}` candidates",
        f"Errors: `{total_errors}` · Warnings: `{total_warnings}`",
        "",
    ]
    for review in reviews:
        fixture_id = review.fixture.get("fixture_id", "unknown")
        lines.extend(
            [
                "---",
                "",
                f"## {fixture_id}",
                "",
                f"Score: `{review.score.score}` · Errors: `{review.score.error_count}` · Warnings: `{review.score.warning_count}`",
                f"Rows parsed: `{review.parsed_row_count}` · Days rendered: `{review.rendered_day_count}`",
                f"Tags: `{', '.join(review.fixture.get('tags', []))}`",
                "",
                f"Trip title: **{review.trip_title or 'MISSING'}**",
                f"Subtitle: {review.trip_subtitle or 'MISSING'}",
                f"Route: {review.route or 'MISSING'}",
                "",
                "### Journey arc",
            ]
        )
        if review.journey_arc:
            for item in review.journey_arc:
                chapter = item.get("chapter", "")
                days = item.get("days", "")
                experience = item.get("experience", "")
                lines.append(f"- **{chapter}** ({days}): {experience}")
        else:
            lines.append("- None detected")
        lines.extend(["", "### Score issues"])
        if review.score.issues:
            for issue in review.score.issues:
                location = f" · `{issue.location}`" if issue.location else ""
                excerpt = f" — {issue.excerpt}" if issue.excerpt else ""
                lines.append(f"- **{issue.severity.upper()} {issue.code}**{location}: {issue.message}{excerpt}")
        else:
            lines.append("- None detected")
        lines.extend(["", "### Days"])
        if not review.days:
            lines.append("No rendered days.")
        for day in review.days:
            lines.extend(
                [
                    "",
                    f"#### {day.day}: {day.title}",
                    f"City: {day.city or 'MISSING'}",
                    f"Intro: {day.intro or 'MISSING'}",
                    "",
                    "Source rows:",
                    *_bullet_lines(day.source_rows, limit=6),
                    "",
                    "Transport:",
                    *_bullet_lines(day.transport),
                    "",
                    "Accommodation:",
                    *_bullet_lines(day.accommodation),
                    "",
                    "Activities:",
                    *_bullet_lines(day.activities),
                    "",
                    "Leisure:",
                    *_bullet_lines(day.leisure),
                    "",
                    "Optional experiences:",
                    *_bullet_lines(day.optional_experiences),
                ]
            )
        lines.extend(["", "### Included", *_bullet_lines(review.included), "", "### Optional add-ons", *_bullet_lines(review.optional_addons), "", "### Not included", *_bullet_lines(review.not_included)])
    return "\n".join(lines).rstrip() + "\n"


def write_reports(markdown: str, json_text: str, *, output_dir: Path, seed: int) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    base = _clean_filename(f"real_output_text_seed_{seed}")
    md_path = output_dir / f"{base}.md"
    json_path = output_dir / f"{base}.json"
    md_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(json_text + "\n", encoding="utf-8")
    return md_path, json_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate readable text reviews from real Excel itinerary fixtures.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Path to real Excel fixture manifest.")
    parser.add_argument("--sample-size", type=int, default=5, help="Number of fixture sheets to sample.")
    parser.add_argument("--seed", default="random", help="Integer seed, or 'random' to generate one and print it.")
    parser.add_argument("--all", action="store_true", help="Review all extractable workbook sheets instead of sampling.")
    parser.add_argument("--workbook", action="append", default=[], help="Restrict to workbook filename substring. Can be repeated.")
    parser.add_argument("--fixture", "--candidate", action="append", default=[], help="Exact fixture id or substring, e.g. 'Standard-Itinerary-Finland.xlsx::106'.")
    parser.add_argument("--output-dir", default=str(DEFAULT_REPORT_DIR), help="Directory for markdown/json reports.")
    parser.add_argument("--stdout", action="store_true", help="Print markdown report instead of writing files.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of markdown when using --stdout.")
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
        print(json_text if args.json else markdown)
    else:
        md_path, json_path = write_reports(markdown, json_text, output_dir=Path(args.output_dir), seed=seed)
        for path in (md_path, json_path):
            try:
                display_path = path.relative_to(ROOT)
            except ValueError:
                display_path = path
            print(f"Wrote {display_path}")
    return 1 if any(review.score.error_count for review in reviews) else 0


if __name__ == "__main__":
    raise SystemExit(main())

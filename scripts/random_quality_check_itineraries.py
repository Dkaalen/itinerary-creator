"""Randomly run real Excel itinerary fixtures through product-output checks."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_modules.itinerary_render_context import build_itinerary_render_context
from generator import group_rows_by_day
from itinerary_generation.copy.phrase_guardrails import contains_banned_generated_phrase
from itinerary_parser import parse_itinerary
from scripts.real_excel_fixture_bank import (
    DEFAULT_MANIFEST,
    ExcelFixtureCandidate,
    build_candidate_index,
    build_index_summary,
    select_random_candidates,
    write_candidate_raw_text,
)

TYPO_LEAKS = (
    "Date dependant",
    "Funicual",
    "Profesional",
    "Free wifi",
    "aiport",
    "doulbe",
    "milage",
)


@dataclass(frozen=True)
class RandomQualityIssue:
    code: str
    severity: str
    message: str
    excerpt: str = ""


@dataclass(frozen=True)
class CandidateReview:
    fixture: dict[str, Any]
    parsed_row_count: int
    rendered_day_count: int
    trip_title: str
    trip_subtitle: str
    issue_count: int
    issues: tuple[RandomQualityIssue, ...]

    @property
    def ok(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)


def _day_text(day: Any) -> str:
    parts = [getattr(day, "title", ""), getattr(day, "intro", "")]
    for block in getattr(day, "blocks", []) or []:
        parts.extend([getattr(block, "title", ""), getattr(block, "description", "")])
    return "\n".join(str(part or "") for part in parts if str(part or "").strip())


def _full_context_text(context: Any) -> str:
    parts = [getattr(context, "trip_title", ""), getattr(context, "trip_subtitle", "")]
    parts.extend(_day_text(day) for day in getattr(context.render_document, "days", []) or [])
    return "\n".join(str(part or "") for part in parts)


def _contains_uncertain_star_upgrade(source_text: str, output_text: str) -> bool:
    if "3/4-star" not in source_text:
        return False
    # A mixed fixture may contain both confirmed 4-star and uncertain 3/4-star
    # stays. Treat it as unsafe only when the uncertain range disappears from
    # the generated output entirely while definite 4-star hotel copy remains.
    if "3/4-star" in output_text:
        return False
    return bool(re.search(r"(?<!3/)\b4-star hotel\b", output_text, flags=re.IGNORECASE))


def _multi_activity_false_open_time(rows: Sequence[dict[str, Any]], days: Iterable[Any]) -> list[RandomQualityIssue]:
    issues: list[RandomQualityIssue] = []
    grouped_rows = group_rows_by_day(rows)
    day_texts = {str(getattr(day, "day", "")): _day_text(day) for day in days}
    for day, day_rows in grouped_rows.items():
        activity_count = sum(1 for row in day_rows if str(row.get("type") or "").casefold() == "activity")
        if activity_count < 2:
            continue
        text = day_texts.get(str(day), "")
        if "rest of the day is open" in text.casefold():
            issues.append(
                RandomQualityIssue(
                    "multi_activity_false_open_time",
                    "error",
                    "Multi-activity day says the rest of the day is open.",
                    str(day),
                )
            )
    return issues


def review_candidate(candidate: ExcelFixtureCandidate) -> CandidateReview:
    issues: list[RandomQualityIssue] = []
    try:
        rows = parse_itinerary(candidate.raw_text)
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        return CandidateReview(
            fixture=candidate.summary(),
            parsed_row_count=0,
            rendered_day_count=0,
            trip_title="",
            trip_subtitle="",
            issue_count=1,
            issues=(RandomQualityIssue("parse_crash", "error", f"Parser crashed: {type(exc).__name__}: {exc}"),),
        )

    if not rows:
        issues.append(RandomQualityIssue("no_parsed_rows", "error", "No itinerary rows parsed from fixture."))
        return CandidateReview(candidate.summary(), 0, 0, "", "", len(issues), tuple(issues))

    try:
        grouped = group_rows_by_day(rows)
        context = build_itinerary_render_context(rows, grouped, {"output_brand": "booknordics_customer"})
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        return CandidateReview(
            fixture=candidate.summary(),
            parsed_row_count=len(rows),
            rendered_day_count=0,
            trip_title="",
            trip_subtitle="",
            issue_count=1,
            issues=(RandomQualityIssue("render_crash", "error", f"Render context crashed: {type(exc).__name__}: {exc}"),),
        )

    output_text = _full_context_text(context)
    rendered_days = tuple(getattr(context.render_document, "days", []) or ())
    if not rendered_days:
        issues.append(RandomQualityIssue("no_rendered_days", "error", "Render context produced no days."))
    if contains_banned_generated_phrase(output_text):
        issues.append(RandomQualityIssue("banned_generated_phrase", "error", "Generated output contains a banned weak phrase."))
    if _contains_uncertain_star_upgrade(candidate.raw_text, output_text):
        issues.append(RandomQualityIssue("uncertain_hotel_star_range_upgraded", "error", "3/4-star source was rendered as definite 4-star hotel."))
    if "Tromsø" in output_text and "Western Norway" in str(getattr(context, "trip_title", "")):
        issues.append(RandomQualityIssue("trip_title_geography_mismatch", "error", "Trip title says Western Norway while output includes Tromsø."))
    for typo in TYPO_LEAKS:
        if typo.casefold() in output_text.casefold():
            issues.append(RandomQualityIssue("supplier_typo_leaked", "error", f"Supplier typo leaked into output: {typo!r}", typo))
    issues.extend(_multi_activity_false_open_time(rows, rendered_days))

    return CandidateReview(
        fixture=candidate.summary(),
        parsed_row_count=len(rows),
        rendered_day_count=len(rendered_days),
        trip_title=str(getattr(context, "trip_title", "")),
        trip_subtitle=str(getattr(context, "trip_subtitle", "")),
        issue_count=len(issues),
        issues=tuple(issues),
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
        "error_count": sum(1 for review in reviews for issue in review.issues if issue.severity == "error"),
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
        "error_count": sum(1 for review in reviews for issue in review.issues if issue.severity == "error"),
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

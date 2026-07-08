"""Markdown report rendering for real-output QA reviews."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Sequence

from scripts.real_excel_fixture_bank import DEFAULT_MANIFEST, build_candidate_index, build_index_summary
from scripts.real_output_qa.models import CandidateOutputReview

DEFAULT_REPORT_DIR = Path(__file__).resolve().parents[2] / "docs/reports/real_output_text_reviews"


def clean_report_filename(value: str) -> str:
    """Return a filesystem-safe report basename."""

    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "report"


def bullet_lines(items: Sequence[str], *, limit: int = 8) -> list[str]:
    """Return compact markdown bullets with an overflow line."""

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
    """Build the human-readable real-output review report."""

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
                f"### {review.journey_title or 'Journey overview'}",
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
        lines.extend(["", "### Human output focus"])
        if review.days:
            for day in review.days:
                leisure_focus = "; ".join(day.leisure[:2]) if day.leisure else "No leisure copy"
                title_source = day.decision_labels.get("title_decision_source", "unknown")
                intro_source = day.decision_labels.get("intro_decision_source", "unknown")
                lines.append(f"- **{day.day}** title: {day.title or 'MISSING'} · Title source: `{title_source}` · Intro source: `{intro_source}` · Intro: {day.intro or 'MISSING'} · Leisure: {leisure_focus}")
        else:
            lines.append("- No rendered days.")

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
                    f"Title decision: `{day.decision_labels.get('title_decision_source', 'unknown')}` — {day.decision_labels.get('title_decision_reason', '')}",
                    f"Intro decision: `{day.decision_labels.get('intro_decision_source', 'unknown')}` — {day.decision_labels.get('intro_decision_reason', '')}",
                    "",
                    "Source rows:",
                    *bullet_lines(day.source_rows, limit=6),
                    "",
                    "Transport:",
                    *bullet_lines(day.transport),
                    "",
                    "Accommodation:",
                    *bullet_lines(day.accommodation),
                    "",
                    "Activities:",
                    *bullet_lines(day.activities),
                    "",
                    "Leisure:",
                    *bullet_lines(day.leisure),
                    "",
                    "Optional experiences:",
                    *bullet_lines(day.optional_experiences),
                ]
            )
        lines.extend(
            [
                "",
                "### Included",
                *bullet_lines(review.included),
                "",
                "### Optional add-ons",
                *bullet_lines(review.optional_addons),
                "",
                "### Not included",
                *bullet_lines(review.not_included),
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_reports(markdown: str, json_text: str, *, output_dir: Path, seed: int) -> tuple[Path, Path]:
    """Write paired markdown/json real-output reports."""

    output_dir.mkdir(parents=True, exist_ok=True)
    base = clean_report_filename(f"real_output_text_seed_{seed}")
    md_path = output_dir / f"{base}.md"
    json_path = output_dir / f"{base}.json"
    md_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(json_text + "\n", encoding="utf-8")
    return md_path, json_path


__all__ = [
    "DEFAULT_REPORT_DIR",
    "build_markdown_report",
    "bullet_lines",
    "clean_report_filename",
    "write_reports",
]

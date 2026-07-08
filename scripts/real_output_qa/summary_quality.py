"""Summary-page quality checks for real-output QA scoring."""

from __future__ import annotations

from typing import Any

from scripts.real_output_qa.models import OutputTextIssue
from scripts.real_output_qa.rules import ARC_LABEL_RE
from scripts.real_output_qa.text_utils import add_issue as _add_issue, clean_text as _clean_text


def score_summary_quality(issues: list[OutputTextIssue], context: Any) -> None:
    """Add journey-summary quality issues for a rendered context."""

    title = _clean_text(getattr(context, "journey_arc_title", ""))
    if title and ARC_LABEL_RE.search(title):
        _add_issue(
            issues,
            "journey_summary_uses_arc_label",
            "error",
            "Trip summary section still uses the weak 'arc' label.",
            location="summary.journey_title",
            excerpt=title,
        )
    arc_rows = [row for row in getattr(context, "journey_arc", []) or () if isinstance(row, dict)]
    seen_experiences: dict[str, str] = {}
    for row in arc_rows:
        chapter = _clean_text(row.get("chapter", ""))
        experience = _clean_text(row.get("experience", ""))
        if not experience:
            _add_issue(
                issues,
                "empty_journey_summary_row",
                "warning",
                "Journey summary row has no experience text.",
                location=f"summary.{chapter}",
            )
            continue
        key = experience.casefold()
        previous = seen_experiences.get(key)
        if previous and chapter.casefold() != previous.casefold():
            _add_issue(
                issues,
                "duplicate_journey_summary_experience",
                "warning",
                "Journey summary repeats the same experience text for multiple chapters.",
                location=f"summary.{chapter}",
                excerpt=experience,
            )
        else:
            seen_experiences[key] = chapter


__all__ = ["score_summary_quality"]

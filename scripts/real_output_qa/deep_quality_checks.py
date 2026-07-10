"""Deep output-quality checks that need cross-section context."""

from __future__ import annotations

import re
from typing import Any, Sequence

from scripts.real_output_qa.models import OutputTextIssue
from scripts.real_output_qa.text_utils import add_issue as _add_issue, clean_text as _clean_text


def score_journey_overview_logic(issues: list[OutputTextIssue], context: Any) -> None:
    """Fail when the journey overview collapses a varied hub stay."""

    arc = tuple(getattr(context, "journey_arc", []) or ())
    for item in arc:
        if not isinstance(item, dict):
            continue
        chapter = _clean_text(item.get("chapter", ""))
        days = _clean_text(item.get("days", ""))
        experience = _clean_text(item.get("experience", ""))
        if re.search(r"\b1\s*-\s*7\b", days) and re.search(
            r"Snæfellsnes|Snaefellsnes",
            experience,
            flags=re.IGNORECASE,
        ):
            _add_issue(
                issues,
                "journey_overview_collapsed_hub_stay",
                "error",
                "Journey overview collapsed a varied hub-based stay into one activity highlight.",
                location=f"journey_overview.{chapter}",
                excerpt=f"{chapter} {days}: {experience}",
            )


def score_unsupported_intro_theme(
    issues: list[OutputTextIssue],
    day_id: str,
    intro: str,
    day_rows: Sequence[dict[str, Any]],
) -> None:
    """Fail when intro copy mentions a theme absent from same-day facts."""

    row_text = " ".join(
        _clean_text(row.get(key, ""))
        for row in day_rows
        for key in ("city", "title", "original_title", "details")
    )
    row_text = f"{row_text} " + " ".join(" ".join(row.get("includes", []) or []) for row in day_rows)
    lower_source = row_text.casefold()
    lower_intro = intro.casefold()
    for rendered_marker, source_marker in (
        ("blue lagoon", "blue lagoon"),
        ("volcano", "volcano"),
        ("whale", "whale"),
    ):
        if rendered_marker in lower_intro and source_marker not in lower_source:
            _add_issue(
                issues,
                "unsupported_intro_theme",
                "error",
                "Day intro mentions a theme not supported by same-day source rows.",
                location=f"{day_id}.intro",
                excerpt=intro,
            )
            return


__all__ = ["score_journey_overview_logic", "score_unsupported_intro_theme"]

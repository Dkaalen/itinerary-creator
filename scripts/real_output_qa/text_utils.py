"""Small text helpers shared by real-output QA modules."""

from __future__ import annotations

import re

from scripts.real_output_qa.models import OutputTextIssue


def clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def clip(value: str, *, limit: int = 180) -> str:
    text = clean_text(value)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def add_issue(
    issues: list[OutputTextIssue],
    code: str,
    severity: str,
    message: str,
    *,
    location: str = "",
    excerpt: str = "",
) -> None:
    issues.append(OutputTextIssue(code=code, severity=severity, message=message, location=location, excerpt=clip(excerpt)))


# Legacy private aliases used by old imports/tests through scripts.real_output_text_quality.
_clean_text = clean_text
_clip = clip
_add_issue = add_issue

__all__ = ["add_issue", "clean_text", "clip", "_add_issue", "_clean_text", "_clip"]

"""Repetition checks for rendered day intros and leisure copy."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Sequence

from scripts.real_output_qa.models import OutputTextIssue
from scripts.real_output_qa.text_utils import add_issue as _add_issue, clean_text as _clean_text

_WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ']+|\d+(?::\d+)?")
_SENTENCE_WORDS = {
    "A",
    "After",
    "An",
    "As",
    "At",
    "Begin",
    "Continue",
    "Drive",
    "Enjoy",
    "Explore",
    "Head",
    "Return",
    "Set",
    "Spend",
    "Start",
    "The",
    "This",
    "Today",
    "Travel",
    "Welcome",
    "With",
    "Your",
}


def _template_tokens(text: str) -> tuple[str, ...]:
    """Normalize variable names and numbers while retaining sentence structure."""

    words = _WORD_RE.findall(_clean_text(text))
    normalized: list[str] = []
    for index, word in enumerate(words):
        if any(character.isdigit() for character in word):
            token = "<value>"
        elif index > 0 and word[:1].isupper() and word not in _SENTENCE_WORDS:
            token = "<name>"
        else:
            token = word.casefold()
        if token == "<name>" and normalized and normalized[-1] == token:
            continue
        normalized.append(token)
    return tuple(normalized)


def _template_similarity(first: str, second: str) -> float:
    first_tokens = _template_tokens(first)
    second_tokens = _template_tokens(second)
    if min(len(first_tokens), len(second_tokens)) < 8:
        return 0.0
    return SequenceMatcher(None, first_tokens, second_tokens, autojunk=False).ratio()


def _similar_group(
    entries: Sequence[tuple[str, str]],
    start_index: int,
    *,
    threshold: float,
) -> tuple[tuple[str, str], ...]:
    anchor = entries[start_index]
    matches = [anchor]
    for candidate in entries[start_index + 1 :]:
        if _template_similarity(anchor[1], candidate[1]) >= threshold:
            matches.append(candidate)
    return tuple(matches)


def _leisure_entries(days: Sequence[Any]) -> tuple[tuple[str, str], ...]:
    entries: list[tuple[str, str]] = []
    for day in days:
        day_id = _clean_text(getattr(day, "day", ""))
        for block in getattr(day, "blocks", []) or ():
            if _clean_text(getattr(block, "kind", "")).casefold() != "leisure":
                continue
            description = _clean_text(getattr(block, "description", ""))
            if len(description) >= 30:
                entries.append((day_id, description))
    return tuple(entries)


def score_repetition(issues: list[OutputTextIssue], days: Sequence[Any]) -> None:
    """Add exact and template-level repetition findings."""

    intro_entries = tuple(
        (_clean_text(getattr(day, "day", "")), _clean_text(getattr(day, "intro", "")))
        for day in days
        if len(_clean_text(getattr(day, "intro", ""))) >= 40
    )

    seen_intros: dict[str, str] = {}
    for day_id, intro in intro_entries:
        previous = seen_intros.get(intro.casefold())
        if previous:
            _add_issue(
                issues,
                "repeated_day_intro",
                "warning",
                "Day intro repeats another day exactly.",
                location=day_id,
                excerpt=f"Same as {previous}: {intro}",
            )
        else:
            seen_intros[intro.casefold()] = day_id

    for index in range(len(intro_entries)):
        group = _similar_group(intro_entries, index, threshold=0.78)
        if len(group) >= 3:
            day_ids = ", ".join(day_id for day_id, _text in group)
            _add_issue(
                issues,
                "templated_day_intro_repetition",
                "warning",
                "Several day intros reuse the same sentence structure with only small substitutions.",
                location=group[-1][0],
                excerpt=f"Similar intro structure across {day_ids}",
            )
            break

    leisure_entries = _leisure_entries(days)
    for index in range(len(leisure_entries)):
        group = _similar_group(leisure_entries, index, threshold=0.82)
        if len(group) >= 3:
            day_ids = ", ".join(day_id for day_id, _text in group)
            _add_issue(
                issues,
                "repeated_leisure_copy",
                "warning",
                "Leisure copy is repeated or lightly reworded across several days.",
                location=group[-1][0],
                excerpt=f"Similar leisure copy across {day_ids}",
            )
            break


__all__ = ["score_repetition"]

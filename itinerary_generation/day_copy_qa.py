"""QA guardrails for generated day intro and leisure copy."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from itinerary_generation.day_facts import DayFacts
from itinerary_generation.day_intent import DayIntent
from shared.text import clean_space

FORBIDDEN_DAY_COPY_PHRASES: tuple[str, ...] = (
    "unhurried",
    "unhurriedly",
    "first impressions",
    "After check-in",
    "after check-in",
    "make your way to your accommodation",
    "Use the remaining time",
)


@dataclass(frozen=True)
class DayCopyIssue:
    code: str
    message: str
    excerpt: str = ""


def _norm(value: object) -> str:
    return clean_space(value)


def _contains(text: str, phrase: str) -> bool:
    return phrase.casefold() in text.casefold()


def find_day_copy_issues(
    *,
    facts: DayFacts,
    intent: DayIntent,
    intro: str = "",
    leisure: str = "",
) -> list[DayCopyIssue]:
    """Return fact-consistency and phrase issues for generated day copy."""

    text = _norm(f"{intro} {leisure}")
    intro_text = _norm(intro)
    leisure_text = _norm(leisure)
    issues: list[DayCopyIssue] = []

    for phrase in FORBIDDEN_DAY_COPY_PHRASES:
        if _contains(text, phrase):
            issues.append(DayCopyIssue("forbidden_phrase", f"Forbidden generated phrase: {phrase!r}", phrase))

    if facts.return_visit and re.search(r"\bWelcome to\b", intro_text, flags=re.IGNORECASE):
        issues.append(DayCopyIssue("return_visit_welcome", "Return visits must not be written as first arrivals.", intro_text))

    if facts.return_visit and re.search(r"\bfirst impressions\b", intro_text, flags=re.IGNORECASE):
        issues.append(DayCopyIssue("return_visit_first_impressions", "Return visits must not mention first impressions.", intro_text))

    if not facts.confirmed_check_in and re.search(r"\bcheck[- ]in\b", intro_text, flags=re.IGNORECASE):
        issues.append(DayCopyIssue("invented_check_in", "Intro mentions check-in without confirmed check-in facts.", intro_text))

    for transit_city in facts.transit_cities:
        if not transit_city:
            continue
        if re.search(rf"\bWelcome to\s+{re.escape(transit_city)}\b", intro_text, flags=re.IGNORECASE):
            issues.append(DayCopyIssue("transit_city_welcome", "Transit-only city is treated as a stay city.", intro_text))

    if facts.full_leisure_day and re.search(r"\bremaining time\b", leisure_text, flags=re.IGNORECASE):
        issues.append(DayCopyIssue("full_leisure_remaining_time", "Full leisure days must not be described as remaining time.", leisure_text))

    if facts.travel_heavy and re.search(r"\bgenerous\b|\bplenty of\b|\bfull day\b", leisure_text, flags=re.IGNORECASE):
        issues.append(DayCopyIssue("overstated_travel_free_time", "Travel-heavy days must not imply generous free time.", leisure_text))

    return issues


def assert_day_copy_clean(*, facts: DayFacts, intent: DayIntent, intro: str = "", leisure: str = "") -> None:
    issues = find_day_copy_issues(facts=facts, intent=intent, intro=intro, leisure=leisure)
    if issues:
        details = "; ".join(f"{issue.code}: {issue.message}" for issue in issues)
        raise AssertionError(details)


def contains_forbidden_day_copy(value: object, phrases: Iterable[str] = FORBIDDEN_DAY_COPY_PHRASES) -> bool:
    text = _norm(value)
    return any(_contains(text, phrase) for phrase in phrases)


__all__ = [
    "DayCopyIssue",
    "FORBIDDEN_DAY_COPY_PHRASES",
    "assert_day_copy_clean",
    "contains_forbidden_day_copy",
    "find_day_copy_issues",
]

"""Shared mechanics for traceable day-title decisions.

This module owns generic title cleaning, shortening, joining and decision-trace
construction. It deliberately contains no day-intent policy.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from itinerary_generation.copy_decision_contract import (
    CopyDecisionCandidate,
    CopyDecisionTrace,
    decision_candidate,
    finalize_decision,
)
from itinerary_generation.title_decision_contract import join_title_text
from shared.text import clean_space
from text_polish import polish_title


def clean_title_value(value: object) -> str:
    return clean_space(value)


def shorten_day_title(value: str) -> str:
    text = clean_title_value(value).strip(" -:|.,")
    lower = text.lower()
    aliases = (
        (("walrus", "safari"), "Walrus Safari"),
        (("reindeer", "sámi"), "Reindeer & Sámi Culture"),
        (("northern lights", "hunt"), "Northern Lights Hunt"),
        (("northern lights", "chase"), "Northern Lights Chase"),
        (("northern lights", "cruise"), "Northern Lights Cruise"),
        (("walking tour", "bergen"), "Bergen Walking Tour"),
    )
    for keywords, alias in aliases:
        if all(keyword in lower for keyword in keywords):
            return alias
    return text


def join_day_titles(first: str, second: str, *, max_length: int = 82) -> str:
    title = join_title_text(first, second, max_length=max_length)
    if len(title) <= max_length:
        return title
    shortened = join_title_text(
        shorten_day_title(first),
        shorten_day_title(second),
        max_length=max_length,
    )
    return shortened if len(shortened) <= max_length else first


def transport_title_candidate(
    text: str,
    *,
    source: str = "transport_title",
    priority: int = 84,
) -> CopyDecisionCandidate | None:
    return decision_candidate(
        polish_title(text),
        source=source,
        priority=priority,
        reason="Transport domain provided the primary route title for this day.",
    )


def title_trace(
    text: str,
    *,
    source: str,
    reason: str,
    candidates: Sequence[CopyDecisionCandidate | None] = (),
    priority: int = 90,
    risk_flags: tuple[str, ...] = (),
    context: Mapping[str, str] | None = None,
) -> CopyDecisionTrace:
    selected = decision_candidate(
        text,
        source=source,
        priority=priority,
        reason=reason,
        risk_flags=risk_flags,
    )
    assert selected is not None
    return finalize_decision(
        kind="day_title",
        selected=selected,
        candidates=candidates,
        context=context,
    )


__all__ = [
    "clean_title_value",
    "join_day_titles",
    "shorten_day_title",
    "title_trace",
    "transport_title_candidate",
]

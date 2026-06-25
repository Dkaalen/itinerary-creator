"""Shared text helpers for trip summaries and journey arcs."""

from __future__ import annotations

from itinerary_generation.client_text_decisions import (
    choose_journey_arc_phrase,
    sanitize_journey_arc_phrase,
    welcome_arc_phrase,
)


def _has(text, *markers):
    return any(marker in text for marker in markers)

def _add_theme(items, theme):
    if theme and theme not in items:
        items.append(theme)

def _welcome_arc_phrase(chapter: str = "") -> str:
    """Compatibility wrapper for the shared Journey Arc fallback rule."""

    return welcome_arc_phrase(chapter)

def sanitize_journey_arc_experience(text: str, *, chapter: str = "") -> str:
    """Compatibility wrapper for shared Journey Arc sanitising."""

    return sanitize_journey_arc_phrase(text, chapter=chapter)

def _title_case_arc(text: str) -> str:
    text = sanitize_journey_arc_phrase(text)
    if not text:
        return "Time to explore at your own pace"
    return text[:1].upper() + text[1:]

def _compact_arc_phrase(candidates, *, chapter: str = ""):
    """Compatibility wrapper for shared compact Journey Arc selection."""

    return choose_journey_arc_phrase(candidates, chapter=chapter)

"""Guardrails for deterministic generated copy.

The app must keep copy deterministic, but generated wording still needs one
shared place for weak phrase bans so preview, PDF and tests do not drift.
"""

from __future__ import annotations

import re

BANNED_GENERATED_PHRASES: tuple[str, ...] = (
    "Begin with Oslo from the water",
    "route presented clearly as part of the day’s experience",
    "route presented clearly as part of the day's experience",
    "clear travel rhythm",
    "quiet outdoor rhythm",
    "rhythm of the voyage",
    "the destination",
    "unhurried",
    "unhurriedly",
    "first impressions",
    "After check-in",
    "make your way to your accommodation",
    "Use the remaining time",
)

_BANNED_RE = re.compile("|".join(re.escape(phrase) for phrase in BANNED_GENERATED_PHRASES), re.IGNORECASE)


def contains_banned_generated_phrase(value: object) -> bool:
    """Return true when generated copy contains a known weak phrase."""

    return bool(_BANNED_RE.search(str(value or "")))


def assert_no_banned_generated_phrase(value: object) -> None:
    """Raise an assertion-friendly error for banned generated wording."""

    text = str(value or "")
    match = _BANNED_RE.search(text)
    if match:
        raise AssertionError(f"Banned generated copy phrase: {match.group(0)!r}")

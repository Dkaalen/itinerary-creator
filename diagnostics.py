"""
diagnostics.py

Collects parser/runtime warnings and unknown patterns during a single generation
run. Warnings are shown in the Streamlit UI so new itinerary formats and runtime
configuration problems can be identified instead of being swallowed silently.
"""

from __future__ import annotations

from contextlib import contextmanager

_warnings: list[dict[str, str]] = []


def reset():
    """Clear warnings at the start of a generation run."""
    global _warnings
    _warnings = []


def _entry(category, message, raw_value="", *, source="") -> dict[str, str]:
    return {
        "category": str(category or "general"),
        "message": str(message or ""),
        "raw": str(raw_value or ""),
        "source": str(source or ""),
    }


def warn(category, message, raw_value="", *, source=""):
    """Record one diagnostic warning, avoiding exact duplicates."""
    entry = _entry(category, message, raw_value, source=source)
    if entry not in _warnings:
        _warnings.append(entry)


def warn_exception(category, message, error, raw_value="", *, source=""):
    """Record an exception as a visible diagnostic without exposing stack noise."""
    error_text = f"{type(error).__name__}: {error}" if error else ""
    detail = " | ".join(part for part in [str(raw_value or ""), error_text] if part)
    warn(category, message, detail, source=source)


def get_warnings():
    return list(_warnings)


@contextmanager
def capture_warnings():
    """Collect warnings for one isolated parse without mutating the active run."""

    global _warnings
    previous = _warnings
    captured: list[dict[str, str]] = []
    _warnings = captured
    try:
        yield captured
    finally:
        _warnings = previous

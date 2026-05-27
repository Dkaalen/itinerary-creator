"""
diagnostics.py

Collects parser warnings and unknown patterns during a single generation run.
Warnings are shown in the Streamlit UI so new itinerary formats can be
identified and taught to the parser over time.
"""

_warnings = []


def reset():
    """Clear warnings at the start of a generation run."""
    global _warnings
    _warnings = []


def warn(category, message, raw_value=""):
    """Record one diagnostic warning, avoiding exact duplicates."""
    entry = {
        "category": str(category or "general"),
        "message": str(message or ""),
        "raw": str(raw_value or ""),
    }
    if entry not in _warnings:
        _warnings.append(entry)


def get_warnings():
    return list(_warnings)

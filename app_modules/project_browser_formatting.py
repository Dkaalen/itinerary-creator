"""Formatting helpers for cloud project browser timestamps."""

from __future__ import annotations


def short_storage_time(value: object) -> str:
    """Return a compact human-readable storage timestamp."""

    text = str(value or "").replace("T", " ").replace("Z", " UTC")
    return text[:19] if text else "Saved project"

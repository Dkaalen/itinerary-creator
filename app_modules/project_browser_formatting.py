"""Formatting helpers for cloud project browser timestamps."""

from __future__ import annotations

from datetime import datetime, timezone


def short_storage_time(value: object) -> str:
    """Return a compact human-readable storage timestamp."""

    text = str(value or "").replace("T", " ").replace("Z", " UTC")
    return text[:19] if text else "Saved project"


def friendly_storage_time(value: object, *, now: datetime | None = None) -> str:
    """Return a compact relative timestamp for project lists and details."""

    parsed = _parse_storage_time(value)
    if parsed is None:
        return "Not saved yet"
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    local_value = parsed.astimezone(reference.tzinfo)
    day_difference = (reference.date() - local_value.date()).days
    clock = local_value.strftime("%H:%M")
    if day_difference == 0:
        return f"Today, {clock}"
    if day_difference == 1:
        return f"Yesterday, {clock}"
    if local_value.year == reference.year:
        return local_value.strftime("%d %b, %H:%M").lstrip("0")
    return local_value.strftime("%d %b %Y").lstrip("0")


def _parse_storage_time(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed

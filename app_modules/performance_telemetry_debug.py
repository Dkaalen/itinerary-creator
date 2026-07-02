"""Developer-only formatting for internal timing telemetry."""

from __future__ import annotations

from typing import Any, Mapping

from app_modules.performance_telemetry import timing_events


def build_timing_summary(state: Mapping[str, Any]) -> str:
    """Return a compact text summary without exposing itinerary content."""

    events = timing_events(dict(state))
    if not events:
        return "No timing data recorded."
    lines = ["Workflow timing checkpoints:"]
    for event in events:
        count = event.get("count")
        suffix = f" ({count})" if isinstance(count, int) else ""
        lines.append(f"- {event.get('stage', '')}: {event.get('seconds', 0):.4f}s{suffix}")
    return "\n".join(lines)


__all__ = ["build_timing_summary"]

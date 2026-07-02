"""Internal workflow timing telemetry for slow-path diagnosis.

The collector stores only stage names, durations and counters. It never stores
raw supplier text, itinerary rows, HTML, images, or PDF bytes.
"""

from __future__ import annotations

from contextlib import contextmanager
from time import perf_counter
from typing import Any, Iterator, MutableMapping

TELEMETRY_KEY = "_performance_telemetry"
TELEMETRY_SCHEMA_VERSION = 1
MAX_TIMING_EVENTS = 80

EXPECTED_STAGES = frozenset(
    {
        "parse_input",
        "normalize_rows",
        "generate_itinerary",
        "build_render_context",
        "add_pictures",
        "image_matching",
        "build_editor_payload",
        "apply_editor_changes",
        "create_pdf",
        "pdf_download_ready",
    }
)


def reset_performance_telemetry(state: MutableMapping[str, Any]) -> None:
    """Start a fresh in-memory timing collection for one workflow run."""

    state[TELEMETRY_KEY] = {"schema_version": TELEMETRY_SCHEMA_VERSION, "events": []}


def _telemetry_payload(state: MutableMapping[str, Any]) -> dict[str, Any]:
    payload = state.get(TELEMETRY_KEY)
    if not isinstance(payload, dict):
        reset_performance_telemetry(state)
        payload = state[TELEMETRY_KEY]
    events = payload.get("events")
    if not isinstance(events, list):
        payload["events"] = []
    payload["schema_version"] = TELEMETRY_SCHEMA_VERSION
    return payload


def record_timing(
    state: MutableMapping[str, Any],
    stage: str,
    seconds: float,
    *,
    count: int | None = None,
    note: str = "",
) -> None:
    """Record one sanitized timing event in session state."""

    stage_name = str(stage or "").strip()
    if not stage_name:
        return
    payload = _telemetry_payload(state)
    events = payload.setdefault("events", [])
    if not isinstance(events, list):
        events = []
        payload["events"] = events
    event: dict[str, Any] = {
        "stage": stage_name,
        "seconds": round(max(0.0, float(seconds or 0.0)), 4),
    }
    if count is not None:
        event["count"] = max(0, int(count))
    if note:
        event["note"] = str(note)[:80]
    events.append(event)
    del events[:-MAX_TIMING_EVENTS]


@contextmanager
def measure_timing(
    state: MutableMapping[str, Any] | None,
    stage: str,
    *,
    count: int | None = None,
    note: str = "",
) -> Iterator[None]:
    """Measure a workflow block without making telemetry required."""

    started = perf_counter()
    try:
        yield
    finally:
        if state is not None:
            record_timing(state, stage, perf_counter() - started, count=count, note=note)


def timing_events(state: MutableMapping[str, Any] | dict[str, Any]) -> tuple[dict[str, Any], ...]:
    """Return a sanitized immutable view of collected timing events."""

    payload = state.get(TELEMETRY_KEY) if isinstance(state, dict) else None
    events = payload.get("events") if isinstance(payload, dict) else []
    if not isinstance(events, list):
        return ()
    return tuple(dict(event) for event in events if isinstance(event, dict))


__all__ = [
    "EXPECTED_STAGES",
    "TELEMETRY_KEY",
    "measure_timing",
    "record_timing",
    "reset_performance_telemetry",
    "timing_events",
]

"""Bounded, sanitized performance and operation telemetry.

The collector is intentionally session-local. It stores stage names, durations,
small counters, request endpoint categories and project identifiers needed to
reproduce Project Explorer state transitions. It never stores supplier text,
itinerary rows, HTML, images, file payloads, Supabase credentials, URLs with
query values, or browser-storage values.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
from contextlib import contextmanager
from statistics import median
from time import perf_counter
from typing import Any, Iterator
from uuid import uuid4

TELEMETRY_KEY = "_performance_telemetry"
TELEMETRY_SCHEMA_VERSION = 2
MAX_TIMING_EVENTS = 160
MAX_TRACE_EVENTS = 160
MAX_REQUEST_RERUNS = 30
MAX_SEQUENCE_ITEMS = 25
MAX_TEXT_LENGTH = 160

EXPECTED_STAGES = frozenset(
    {
        "streamlit_rerun",
        "project_explorer_render",
        "project_list_management",
        "project_list_legacy",
        "project_folder_list",
        "project_delete_batch",
        "supplier_preview_parse",
        "unsaved_state_check",
        "supabase_request",
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
    """Start a fresh workflow timing collection without erasing app traces."""

    existing = state.get(TELEMETRY_KEY)
    if not isinstance(existing, Mapping):
        existing = {}
    state[TELEMETRY_KEY] = {
        "schema_version": TELEMETRY_SCHEMA_VERSION,
        "events": [],
        "traces": list(existing.get("traces") or [])[-MAX_TRACE_EVENTS:],
        "rerun_number": _non_negative_int(existing.get("rerun_number")),
        "sequence": _non_negative_int(existing.get("sequence")),
        "request_count_total": _non_negative_int(existing.get("request_count_total")),
        "request_count_by_rerun": _clean_request_counts(existing.get("request_count_by_rerun")),
    }


def telemetry_is_active(state: Mapping[str, Any] | None) -> bool:
    """Return whether the current mapping owns an initialized telemetry payload."""

    return bool(state is not None and isinstance(state.get(TELEMETRY_KEY), Mapping))


def begin_rerun(state: MutableMapping[str, Any]) -> int:
    """Advance the bounded Streamlit rerun counter and record one marker."""

    payload = _telemetry_payload(state)
    rerun_number = _non_negative_int(payload.get("rerun_number")) + 1
    payload["rerun_number"] = rerun_number
    request_counts = _clean_request_counts(payload.get("request_count_by_rerun"))
    request_counts[str(rerun_number)] = 0
    payload["request_count_by_rerun"] = _bounded_request_counts(request_counts)
    record_trace(state, "streamlit_rerun_started", rerun=rerun_number)
    return rerun_number


def current_rerun_number(state: Mapping[str, Any] | None) -> int:
    payload = state.get(TELEMETRY_KEY) if state is not None else None
    if not isinstance(payload, Mapping):
        return 0
    return _non_negative_int(payload.get("rerun_number"))


def new_operation_id(prefix: str) -> str:
    """Return a compact correlation id without embedding user data."""

    clean_prefix = "".join(character for character in str(prefix or "") if character.isalnum() or character in "_-")
    return f"{clean_prefix or 'operation'}-{uuid4().hex[:12]}"


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
        "stage": stage_name[:80],
        "seconds": round(max(0.0, float(seconds or 0.0)), 4),
        "rerun": current_rerun_number(state),
        "sequence": _next_sequence(payload),
    }
    if count is not None:
        event["count"] = max(0, int(count))
    if note:
        event["note"] = str(note)[:80]
    events.append(event)
    del events[:-MAX_TIMING_EVENTS]


def record_trace(
    state: MutableMapping[str, Any],
    event: str,
    **fields: Any,
) -> None:
    """Record one bounded state-transition event with sanitized scalar fields."""

    event_name = str(event or "").strip()
    if not event_name:
        return
    payload = _telemetry_payload(state)
    traces = payload.setdefault("traces", [])
    if not isinstance(traces, list):
        traces = []
        payload["traces"] = traces
    entry: dict[str, Any] = {
        "event": event_name[:80],
        "rerun": current_rerun_number(state),
        "sequence": _next_sequence(payload),
    }
    for key, value in fields.items():
        clean_key = "".join(character for character in str(key or "") if character.isalnum() or character == "_")[:48]
        if not clean_key or clean_key in entry:
            continue
        sanitized = _sanitized_value(value)
        if sanitized is not None:
            entry[clean_key] = sanitized
    traces.append(entry)
    del traces[:-MAX_TRACE_EVENTS]


def record_supabase_request(state: MutableMapping[str, Any], request_event: Mapping[str, Any]) -> None:
    """Record one low-level request without retaining URL parameters or payloads."""

    payload = _telemetry_payload(state)
    rerun_number = current_rerun_number(state)
    payload["request_count_total"] = _non_negative_int(payload.get("request_count_total")) + 1
    request_counts = _clean_request_counts(payload.get("request_count_by_rerun"))
    request_counts[str(rerun_number)] = _non_negative_int(request_counts.get(str(rerun_number))) + 1
    payload["request_count_by_rerun"] = _bounded_request_counts(request_counts)

    seconds = max(0.0, float(request_event.get("seconds") or 0.0))
    method = str(request_event.get("method") or "").upper()[:12]
    endpoint = str(request_event.get("endpoint") or "unknown")[:80]
    record_timing(state, "supabase_request", seconds, note=f"{method} {endpoint}".strip())
    record_trace(
        state,
        "supabase_request",
        request_id=request_event.get("request_id"),
        method=method,
        endpoint=endpoint,
        ok=bool(request_event.get("ok")),
        status=request_event.get("status"),
        seconds=round(seconds, 4),
        request_bytes=request_event.get("request_bytes"),
        response_bytes=request_event.get("response_bytes"),
        error_type=request_event.get("error_type"),
    )


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


def timing_events(state: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Return a sanitized immutable view of collected timing events."""

    payload = state.get(TELEMETRY_KEY) if isinstance(state, Mapping) else None
    events = payload.get("events") if isinstance(payload, Mapping) else []
    if not isinstance(events, list):
        return ()
    return tuple(dict(event) for event in events if isinstance(event, Mapping))


def trace_events(state: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Return a sanitized immutable view of recent transition events."""

    payload = state.get(TELEMETRY_KEY) if isinstance(state, Mapping) else None
    traces = payload.get("traces") if isinstance(payload, Mapping) else []
    if not isinstance(traces, list):
        return ()
    return tuple(dict(event) for event in traces if isinstance(event, Mapping))


def timing_summary(state: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Return p50 and worst observed duration per measured stage."""

    grouped: dict[str, list[float]] = {}
    for event in timing_events(state):
        stage = str(event.get("stage") or "").strip()
        if not stage:
            continue
        grouped.setdefault(stage, []).append(max(0.0, float(event.get("seconds") or 0.0)))
    result = []
    for stage in sorted(grouped):
        values = grouped[stage]
        result.append(
            {
                "stage": stage,
                "samples": len(values),
                "p50_ms": round(median(values) * 1000, 2),
                "worst_ms": round(max(values) * 1000, 2),
            }
        )
    return tuple(result)


def telemetry_snapshot(state: Mapping[str, Any]) -> dict[str, Any]:
    """Return one export-safe snapshot for debug review or test artifacts."""

    payload = state.get(TELEMETRY_KEY) if isinstance(state, Mapping) else None
    if not isinstance(payload, Mapping):
        return {
            "schema_version": TELEMETRY_SCHEMA_VERSION,
            "rerun_number": 0,
            "request_count_total": 0,
            "request_count_by_rerun": {},
            "timing_summary": [],
            "timings": [],
            "traces": [],
        }
    return {
        "schema_version": TELEMETRY_SCHEMA_VERSION,
        "rerun_number": _non_negative_int(payload.get("rerun_number")),
        "request_count_total": _non_negative_int(payload.get("request_count_total")),
        "request_count_by_rerun": _clean_request_counts(payload.get("request_count_by_rerun")),
        "timing_summary": [dict(item) for item in timing_summary(state)],
        "timings": [dict(item) for item in timing_events(state)],
        "traces": [dict(item) for item in trace_events(state)],
    }


def _telemetry_payload(state: MutableMapping[str, Any]) -> dict[str, Any]:
    payload = state.get(TELEMETRY_KEY)
    if not isinstance(payload, dict):
        reset_performance_telemetry(state)
        payload = state[TELEMETRY_KEY]
    events = payload.get("events")
    if not isinstance(events, list):
        payload["events"] = []
    traces = payload.get("traces")
    if not isinstance(traces, list):
        payload["traces"] = []
    payload["schema_version"] = TELEMETRY_SCHEMA_VERSION
    return payload


def _next_sequence(payload: MutableMapping[str, Any]) -> int:
    sequence = _non_negative_int(payload.get("sequence")) + 1
    payload["sequence"] = sequence
    return sequence


def _sanitized_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return round(max(0.0, value), 4)
    if isinstance(value, str):
        return value[:MAX_TEXT_LENGTH]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        result = []
        for item in value[:MAX_SEQUENCE_ITEMS]:
            sanitized = _sanitized_value(item)
            if sanitized is not None and not isinstance(sanitized, (dict, list)):
                result.append(sanitized)
        return result
    return str(value)[:MAX_TEXT_LENGTH]


def _clean_request_counts(value: Any) -> dict[str, int]:
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, int] = {}
    for key, count in value.items():
        clean_key = str(key or "").strip()
        if clean_key:
            result[clean_key[:16]] = _non_negative_int(count)
    return _bounded_request_counts(result)


def _bounded_request_counts(value: Mapping[str, int]) -> dict[str, int]:
    ordered = sorted(value.items(), key=lambda item: _non_negative_int(item[0]))
    return {key: _non_negative_int(count) for key, count in ordered[-MAX_REQUEST_RERUNS:]}


def _non_negative_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


__all__ = [
    "EXPECTED_STAGES",
    "TELEMETRY_KEY",
    "begin_rerun",
    "current_rerun_number",
    "measure_timing",
    "new_operation_id",
    "record_supabase_request",
    "record_timing",
    "record_trace",
    "reset_performance_telemetry",
    "telemetry_is_active",
    "telemetry_snapshot",
    "timing_events",
    "timing_summary",
    "trace_events",
]

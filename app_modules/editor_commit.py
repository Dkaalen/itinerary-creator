"""Visual-editor commit coordination for hard workflow transitions.

The browser visual editor can hold unsaved edits that Streamlit does not see
until the component sends a save payload.  Hard workflow transitions such as
Add Pictures and Create PDF must therefore request a full visible-model commit
before they read from server-side itinerary state.
"""

from __future__ import annotations

from collections.abc import MutableMapping
from time import time
from typing import Any

VISUAL_EDITOR_COMMIT_COUNTER_KEY = "_visual_editor_commit_counter"
VISUAL_EDITOR_COMMIT_NONCE_KEY = "_visual_editor_commit_nonce"
VISUAL_EDITOR_LAST_APPLIED_COMMIT_KEY = "_visual_editor_last_applied_commit_nonce"
VISUAL_EDITOR_COMMIT_TIMEOUT_SECONDS = 20.0
PDF_EDITOR_COMMIT_TIMEOUT_SECONDS = 10.0

PDF_COMMIT_REQUEST_KEY = "_pdf_after_visual_edit_commit_nonce"
PDF_COMMIT_READY_KEY = "_visual_editor_export_commit_ready"
PDF_COMMIT_REQUESTED_AT_KEY = "_pdf_after_visual_edit_commit_requested_at"

ADD_PICTURES_COMMIT_REQUEST_KEY = "_add_pictures_after_visual_edit_commit_nonce"
ADD_PICTURES_COMMIT_READY_KEY = "_visual_editor_add_pictures_commit_ready"
ADD_PICTURES_COMMIT_REQUESTED_AT_KEY = "_add_pictures_after_visual_edit_commit_requested_at"


def _timestamp(now: float | None = None) -> float:
    return float(time() if now is None else now)


def _next_commit_nonce(state: MutableMapping[str, Any]) -> str:
    next_nonce = str(int(state.get(VISUAL_EDITOR_COMMIT_COUNTER_KEY, 0)) + 1)
    state[VISUAL_EDITOR_COMMIT_COUNTER_KEY] = int(next_nonce)
    return next_nonce


def request_visual_editor_commit(
    state: MutableMapping[str, Any],
    *,
    request_key: str,
    ready_key: str,
    requested_at_key: str | None = None,
    now: float | None = None,
) -> str:
    """Ask the frontend editor to commit its current visible edits.

    A single ``_visual_editor_commit_nonce`` is rendered into the component. The
    target-specific request and ready keys let the server tell whether that
    committed payload belongs to Add Pictures or PDF export.
    """

    next_nonce = _next_commit_nonce(state)
    state[VISUAL_EDITOR_COMMIT_NONCE_KEY] = next_nonce
    state[request_key] = next_nonce
    state[ready_key] = False
    if requested_at_key:
        state[requested_at_key] = _timestamp(now)
    return next_nonce


def visual_editor_commit_ready(
    state: MutableMapping[str, Any],
    *,
    request_key: str,
    ready_key: str,
) -> bool:
    """Return whether the requested full-model commit has been applied."""

    requested_commit_nonce = state.get(request_key)
    return bool(
        requested_commit_nonce
        and state.get(ready_key)
        and str(state.get(VISUAL_EDITOR_LAST_APPLIED_COMMIT_KEY, "")) == str(requested_commit_nonce)
    )


def visual_editor_commit_elapsed_seconds(
    state: MutableMapping[str, Any],
    *,
    requested_at_key: str,
    now: float | None = None,
) -> float:
    """Return how long the current commit request has been waiting."""

    try:
        started_at = float(state.get(requested_at_key) or 0.0)
    except (TypeError, ValueError):
        started_at = 0.0
    if started_at <= 0:
        return 0.0
    return max(0.0, _timestamp(now) - started_at)


def visual_editor_commit_timed_out(
    state: MutableMapping[str, Any],
    *,
    request_key: str,
    ready_key: str,
    requested_at_key: str,
    timeout_seconds: float = VISUAL_EDITOR_COMMIT_TIMEOUT_SECONDS,
    now: float | None = None,
) -> bool:
    """Return True when the browser has not answered a pending commit in time."""

    if not state.get(request_key) or visual_editor_commit_ready(state, request_key=request_key, ready_key=ready_key):
        return False
    return visual_editor_commit_elapsed_seconds(state, requested_at_key=requested_at_key, now=now) >= float(timeout_seconds)


def clear_visual_editor_commit_request(
    state: MutableMapping[str, Any],
    *,
    request_key: str,
    ready_key: str,
    requested_at_key: str | None = None,
) -> None:
    """Clear a completed or abandoned editor-commit request."""

    requested_commit_nonce = state.get(request_key)
    state[request_key] = None
    state[ready_key] = False
    if requested_at_key:
        state.pop(requested_at_key, None)
    if requested_commit_nonce and str(state.get(VISUAL_EDITOR_COMMIT_NONCE_KEY, "")) == str(requested_commit_nonce):
        state[VISUAL_EDITOR_COMMIT_NONCE_KEY] = None


def request_pdf_editor_commit(state: MutableMapping[str, Any], *, now: float | None = None) -> str:
    return request_visual_editor_commit(
        state,
        request_key=PDF_COMMIT_REQUEST_KEY,
        ready_key=PDF_COMMIT_READY_KEY,
        requested_at_key=PDF_COMMIT_REQUESTED_AT_KEY,
        now=now,
    )


def pdf_editor_commit_ready(state: MutableMapping[str, Any]) -> bool:
    return visual_editor_commit_ready(
        state,
        request_key=PDF_COMMIT_REQUEST_KEY,
        ready_key=PDF_COMMIT_READY_KEY,
    )


def pdf_editor_commit_timed_out(
    state: MutableMapping[str, Any],
    *,
    timeout_seconds: float = PDF_EDITOR_COMMIT_TIMEOUT_SECONDS,
    now: float | None = None,
) -> bool:
    return visual_editor_commit_timed_out(
        state,
        request_key=PDF_COMMIT_REQUEST_KEY,
        ready_key=PDF_COMMIT_READY_KEY,
        requested_at_key=PDF_COMMIT_REQUESTED_AT_KEY,
        timeout_seconds=timeout_seconds,
        now=now,
    )


def pdf_editor_commit_elapsed_seconds(state: MutableMapping[str, Any], *, now: float | None = None) -> float:
    return visual_editor_commit_elapsed_seconds(state, requested_at_key=PDF_COMMIT_REQUESTED_AT_KEY, now=now)


def clear_pdf_editor_commit_request(state: MutableMapping[str, Any]) -> None:
    clear_visual_editor_commit_request(
        state,
        request_key=PDF_COMMIT_REQUEST_KEY,
        ready_key=PDF_COMMIT_READY_KEY,
        requested_at_key=PDF_COMMIT_REQUESTED_AT_KEY,
    )


def request_add_pictures_editor_commit(state: MutableMapping[str, Any], *, now: float | None = None) -> str:
    return request_visual_editor_commit(
        state,
        request_key=ADD_PICTURES_COMMIT_REQUEST_KEY,
        ready_key=ADD_PICTURES_COMMIT_READY_KEY,
        requested_at_key=ADD_PICTURES_COMMIT_REQUESTED_AT_KEY,
        now=now,
    )


def add_pictures_editor_commit_ready(state: MutableMapping[str, Any]) -> bool:
    return visual_editor_commit_ready(
        state,
        request_key=ADD_PICTURES_COMMIT_REQUEST_KEY,
        ready_key=ADD_PICTURES_COMMIT_READY_KEY,
    )


def add_pictures_editor_commit_timed_out(
    state: MutableMapping[str, Any],
    *,
    timeout_seconds: float = VISUAL_EDITOR_COMMIT_TIMEOUT_SECONDS,
    now: float | None = None,
) -> bool:
    return visual_editor_commit_timed_out(
        state,
        request_key=ADD_PICTURES_COMMIT_REQUEST_KEY,
        ready_key=ADD_PICTURES_COMMIT_READY_KEY,
        requested_at_key=ADD_PICTURES_COMMIT_REQUESTED_AT_KEY,
        timeout_seconds=timeout_seconds,
        now=now,
    )


def add_pictures_editor_commit_elapsed_seconds(state: MutableMapping[str, Any], *, now: float | None = None) -> float:
    return visual_editor_commit_elapsed_seconds(state, requested_at_key=ADD_PICTURES_COMMIT_REQUESTED_AT_KEY, now=now)


def clear_add_pictures_editor_commit_request(state: MutableMapping[str, Any]) -> None:
    clear_visual_editor_commit_request(
        state,
        request_key=ADD_PICTURES_COMMIT_REQUEST_KEY,
        ready_key=ADD_PICTURES_COMMIT_READY_KEY,
        requested_at_key=ADD_PICTURES_COMMIT_REQUESTED_AT_KEY,
    )

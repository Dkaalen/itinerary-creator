"""Session-state helpers for the PDF export job lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from time import time
from typing import Any, Mapping, MutableMapping

PDF_EXPORT_JOB_KEY = "_pdf_export_job"
PDF_AUTO_CREATE_REQUEST_KEY = "_pdf_auto_create_requested"

_EXPORT_JOB_DEFAULTS: dict[str, Any] = {
    "state": "idle",
    "message": "",
    "started_at": 0.0,
    "updated_at": 0.0,
    "commit_nonce": "",
    "error": "",
    "signature": "",
}


@dataclass(frozen=True)
class PdfExportJob:
    """Compact user-flow state for PDF creation."""

    state: str
    message: str = ""
    started_at: float = 0.0
    updated_at: float = 0.0
    commit_nonce: str = ""
    error: str = ""
    signature: str = ""

    @property
    def waiting_for_editor(self) -> bool:
        return self.state == "saving"

    @property
    def exporting(self) -> bool:
        return self.state == "exporting"

    @property
    def ready(self) -> bool:
        return self.state == "ready"

    @property
    def failed(self) -> bool:
        return self.state == "failed"


def _timestamp(now: float | None = None) -> float:
    return float(time() if now is None else now)


def _job_payload(state: str, *, now: float | None = None, **overrides: Any) -> dict[str, Any]:
    timestamp = _timestamp(now)
    payload = dict(_EXPORT_JOB_DEFAULTS)
    payload.update({"state": state, "started_at": timestamp, "updated_at": timestamp})
    payload.update(overrides)
    return payload


def current_export_job(state: Mapping[str, Any]) -> PdfExportJob:
    raw = state.get(PDF_EXPORT_JOB_KEY)
    payload = dict(_EXPORT_JOB_DEFAULTS)
    if isinstance(raw, Mapping):
        payload.update({key: raw.get(key, value) for key, value in _EXPORT_JOB_DEFAULTS.items()})
    return PdfExportJob(
        state=str(payload.get("state") or "idle"),
        message=str(payload.get("message") or ""),
        started_at=float(payload.get("started_at") or 0.0),
        updated_at=float(payload.get("updated_at") or 0.0),
        commit_nonce=str(payload.get("commit_nonce") or ""),
        error=str(payload.get("error") or ""),
        signature=str(payload.get("signature") or ""),
    )


def request_auto_pdf_create(state: MutableMapping[str, Any]) -> None:
    """Ask the export page to start one PDF job after it renders the editor."""

    state[PDF_AUTO_CREATE_REQUEST_KEY] = True


def auto_pdf_create_requested(state: Mapping[str, Any]) -> bool:
    """Return whether a queued automatic PDF request is still waiting."""

    return bool(state.get(PDF_AUTO_CREATE_REQUEST_KEY))


def consume_auto_pdf_create_request(state: MutableMapping[str, Any]) -> bool:
    """Return and clear the automatic PDF request flag."""

    requested = auto_pdf_create_requested(state)
    state[PDF_AUTO_CREATE_REQUEST_KEY] = False
    return requested


def mark_export_waiting_for_editor(
    state: MutableMapping[str, Any],
    *,
    commit_nonce: str,
    now: float | None = None,
) -> PdfExportJob:
    """Record that PDF export is waiting for one editor save payload."""

    state[PDF_EXPORT_JOB_KEY] = _job_payload(
        "saving",
        now=now,
        commit_nonce=str(commit_nonce or ""),
        message="Saving latest edits before PDF export.",
    )
    return current_export_job(state)


def mark_exporting(state: MutableMapping[str, Any], *, signature: str | None = None, now: float | None = None) -> PdfExportJob:
    """Record that PDF byte generation is running."""

    previous = current_export_job(state)
    started_at = previous.started_at or _timestamp(now)
    timestamp = _timestamp(now)
    state[PDF_EXPORT_JOB_KEY] = {
        **_EXPORT_JOB_DEFAULTS,
        "state": "exporting",
        "message": "Creating PDF.",
        "started_at": started_at,
        "updated_at": timestamp,
        "commit_nonce": previous.commit_nonce,
        "signature": str(signature or previous.signature or ""),
    }
    return current_export_job(state)


def mark_export_ready(state: MutableMapping[str, Any], *, signature: str | None = None, now: float | None = None) -> PdfExportJob:
    """Record that a current PDF exists."""

    previous = current_export_job(state)
    started_at = previous.started_at or _timestamp(now)
    timestamp = _timestamp(now)
    state[PDF_EXPORT_JOB_KEY] = {
        **_EXPORT_JOB_DEFAULTS,
        "state": "ready",
        "message": "PDF ready.",
        "started_at": started_at,
        "updated_at": timestamp,
        "signature": str(signature or previous.signature or ""),
    }
    return current_export_job(state)


def mark_export_failed(state: MutableMapping[str, Any], *, error: str, now: float | None = None) -> PdfExportJob:
    """Record a recoverable PDF export failure."""

    previous = current_export_job(state)
    started_at = previous.started_at or _timestamp(now)
    timestamp = _timestamp(now)
    state[PDF_EXPORT_JOB_KEY] = {
        **_EXPORT_JOB_DEFAULTS,
        "state": "failed",
        "message": "PDF export failed.",
        "started_at": started_at,
        "updated_at": timestamp,
        "error": str(error or "PDF export failed."),
        "signature": previous.signature,
    }
    return current_export_job(state)


def reset_export_job(state: MutableMapping[str, Any]) -> None:
    """Clear transient PDF job state without touching generated PDF bytes."""

    state.pop(PDF_EXPORT_JOB_KEY, None)
    state[PDF_AUTO_CREATE_REQUEST_KEY] = False

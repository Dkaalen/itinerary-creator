"""PDF-export save coordination for the visual editor."""

from __future__ import annotations

from time import time
from typing import Any, MutableMapping

from app_modules.editor_commit import (
    PDF_COMMIT_REQUEST_KEY,
    clear_pdf_editor_commit_request,
    pdf_editor_commit_ready,
    request_pdf_editor_commit,
)
from app_modules.export_job_state import (
    PdfExportJob,
    current_export_job,
    mark_export_waiting_for_editor,
    reset_export_job,
)

PDF_EDITOR_SAVE_TIMEOUT_SECONDS = 10.0


def request_editor_save_before_pdf(state: MutableMapping[str, Any], *, now: float | None = None) -> PdfExportJob:
    """Ask the browser editor for one full visible-model save before export."""

    commit_nonce = request_pdf_editor_commit(state)
    return mark_export_waiting_for_editor(state, commit_nonce=commit_nonce, now=now)


def pdf_editor_save_waiting(state: MutableMapping[str, Any]) -> bool:
    """Return whether a PDF export job is waiting for an editor save payload."""

    job = current_export_job(state)
    return job.waiting_for_editor and bool(state.get(PDF_COMMIT_REQUEST_KEY))


def pdf_editor_save_ready(state: MutableMapping[str, Any]) -> bool:
    """Return whether the requested editor save payload has reached the server."""

    return pdf_editor_save_waiting(state) and pdf_editor_commit_ready(state)


def pdf_editor_save_elapsed_seconds(state: MutableMapping[str, Any], *, now: float | None = None) -> float:
    """Return seconds spent waiting for the current editor save."""

    job = current_export_job(state)
    if not job.waiting_for_editor or not job.started_at:
        return 0.0
    return max(0.0, float(time() if now is None else now) - float(job.started_at))


def pdf_editor_save_timed_out(state: MutableMapping[str, Any], *, now: float | None = None) -> bool:
    """Return whether the editor save wait has exceeded its recovery window."""

    return pdf_editor_save_waiting(state) and pdf_editor_save_elapsed_seconds(state, now=now) >= PDF_EDITOR_SAVE_TIMEOUT_SECONDS


def clear_pdf_editor_save(state: MutableMapping[str, Any]) -> None:
    """Abandon a pending editor save request and clear the transient job state."""

    clear_pdf_editor_commit_request(state)
    reset_export_job(state)

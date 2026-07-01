"""Compatibility helpers for the old PDF-export editor-save handshake.

PDF creation now uses the latest server-owned preview state.  These functions
remain for older imports/tests, but they must not start a browser commit wait.
"""

from __future__ import annotations

from time import time
from typing import Any, MutableMapping

from app_modules.editor_commit import clear_pdf_editor_commit_request
from app_modules.export_job_state import PdfExportJob, current_export_job, mark_exporting, reset_export_job

PDF_EDITOR_SAVE_TIMEOUT_SECONDS = 10.0


def request_editor_save_before_pdf(state: MutableMapping[str, Any], *, now: float | None = None) -> PdfExportJob:
    """Compatibility no-op: clear stale waits and continue with PDF export."""

    clear_pdf_editor_commit_request(state)
    return mark_exporting(state, signature=str(state.get("preview_signature") or ""), now=now)


def pdf_editor_save_waiting(state: MutableMapping[str, Any]) -> bool:
    """The active PDF path no longer waits for a browser editor save."""

    return False


def pdf_editor_save_ready(state: MutableMapping[str, Any]) -> bool:
    """Return true when there is no legacy save wait blocking PDF creation."""

    return not pdf_editor_save_waiting(state)


def pdf_editor_save_elapsed_seconds(state: MutableMapping[str, Any], *, now: float | None = None) -> float:
    """Return zero because no PDF editor-save wait is active."""

    _ = current_export_job(state), now, time
    return 0.0


def pdf_editor_save_timed_out(state: MutableMapping[str, Any], *, now: float | None = None) -> bool:
    """The no-wait export path cannot time out waiting for the browser editor."""

    _ = state, now
    return False


def clear_pdf_editor_save(state: MutableMapping[str, Any]) -> None:
    """Abandon stale editor-save/commit state without touching PDF bytes."""

    clear_pdf_editor_commit_request(state)
    reset_export_job(state)

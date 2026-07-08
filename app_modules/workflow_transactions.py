"""Typed workflow transaction helpers for hard browser/server handoffs.

Streamlit pages still own rendering, but workflow transitions such as Add
Pictures and Create PDF now share one small transaction contract instead of
open-coding pending nonce, timeout, fallback, and cancel checks in each page.
"""

from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from app_modules.editor_commit import (
    ADD_PICTURES_COMMIT_REQUEST_KEY,
    PDF_COMMIT_REQUEST_KEY,
    add_pictures_editor_commit_elapsed_seconds,
    add_pictures_editor_commit_ready,
    add_pictures_editor_commit_timed_out,
    clear_add_pictures_editor_commit_request,
    clear_pdf_editor_commit_request,
    pdf_editor_commit_elapsed_seconds,
    pdf_editor_commit_ready,
    pdf_editor_commit_timed_out,
    request_add_pictures_editor_commit,
    request_pdf_editor_commit,
)
from app_modules.export_job_state import mark_export_waiting_for_editor, request_auto_pdf_create, reset_export_job
from app_modules.export_timing import record_pdf_export_marker, reset_pdf_export_timings


class WorkflowTransactionTarget(str, Enum):
    """Hard workflow transitions that require a current browser commit."""

    ADD_PICTURES = "add_pictures"
    CREATE_PDF = "create_pdf"


class WorkflowTransactionStatus(str, Enum):
    """Normalized lifecycle status for a workflow transaction."""

    IDLE = "idle"
    WAITING_FOR_BROWSER = "waiting_for_browser"
    READY = "ready"
    TIMED_OUT = "timed_out"


@dataclass(frozen=True)
class WorkflowTransaction:
    """A normalized view of one pending or ready workflow transition."""

    target: WorkflowTransactionTarget
    status: WorkflowTransactionStatus
    commit_nonce: str = ""
    elapsed_seconds: float = 0.0

    @property
    def pending(self) -> bool:
        return self.status == WorkflowTransactionStatus.WAITING_FOR_BROWSER

    @property
    def ready(self) -> bool:
        return self.status == WorkflowTransactionStatus.READY

    @property
    def timed_out(self) -> bool:
        return self.status == WorkflowTransactionStatus.TIMED_OUT


def workflow_transaction_state(
    state: MutableMapping[str, Any],
    target: WorkflowTransactionTarget | str,
    *,
    now: float | None = None,
) -> WorkflowTransaction:
    """Return the current transaction state for ``target``."""

    resolved = WorkflowTransactionTarget(target)
    if resolved == WorkflowTransactionTarget.ADD_PICTURES:
        nonce = str(state.get(ADD_PICTURES_COMMIT_REQUEST_KEY) or "")
        if add_pictures_editor_commit_ready(state):
            return WorkflowTransaction(resolved, WorkflowTransactionStatus.READY, nonce, add_pictures_editor_commit_elapsed_seconds(state, now=now))
        if not nonce:
            return WorkflowTransaction(resolved, WorkflowTransactionStatus.IDLE)
        elapsed = add_pictures_editor_commit_elapsed_seconds(state, now=now)
        status = WorkflowTransactionStatus.TIMED_OUT if add_pictures_editor_commit_timed_out(state, now=now) else WorkflowTransactionStatus.WAITING_FOR_BROWSER
        return WorkflowTransaction(resolved, status, nonce, elapsed)

    nonce = str(state.get(PDF_COMMIT_REQUEST_KEY) or "")
    if pdf_editor_commit_ready(state):
        return WorkflowTransaction(resolved, WorkflowTransactionStatus.READY, nonce, pdf_editor_commit_elapsed_seconds(state, now=now))
    if not nonce:
        return WorkflowTransaction(resolved, WorkflowTransactionStatus.IDLE)
    elapsed = pdf_editor_commit_elapsed_seconds(state, now=now)
    status = WorkflowTransactionStatus.TIMED_OUT if pdf_editor_commit_timed_out(state, now=now) else WorkflowTransactionStatus.WAITING_FOR_BROWSER
    return WorkflowTransaction(resolved, status, nonce, elapsed)


def start_workflow_transaction(
    state: MutableMapping[str, Any],
    target: WorkflowTransactionTarget | str,
    *,
    auto_create_pdf: bool = False,
    now: float | None = None,
) -> WorkflowTransaction:
    """Request a browser commit and return the resulting transaction state."""

    resolved = WorkflowTransactionTarget(target)
    if resolved == WorkflowTransactionTarget.ADD_PICTURES:
        nonce = request_add_pictures_editor_commit(state, now=now)
        return WorkflowTransaction(resolved, WorkflowTransactionStatus.WAITING_FOR_BROWSER, nonce, 0.0)

    reset_pdf_export_timings(state)
    nonce = request_pdf_editor_commit(state, now=now)
    record_pdf_export_marker(state, "editor_commit_requested", note="create_pdf")
    mark_export_waiting_for_editor(state, commit_nonce=nonce, now=now)
    if auto_create_pdf:
        request_auto_pdf_create(state)
    return WorkflowTransaction(resolved, WorkflowTransactionStatus.WAITING_FOR_BROWSER, nonce, 0.0)


def retry_workflow_transaction(
    state: MutableMapping[str, Any],
    target: WorkflowTransactionTarget | str,
    *,
    auto_create_pdf: bool = False,
    now: float | None = None,
) -> WorkflowTransaction:
    """Start a fresh commit request for a timed-out transaction."""

    clear_workflow_transaction(state, target, clear_export_job=False)
    return start_workflow_transaction(state, target, auto_create_pdf=auto_create_pdf, now=now)


def clear_workflow_transaction(
    state: MutableMapping[str, Any],
    target: WorkflowTransactionTarget | str,
    *,
    clear_export_job: bool = True,
) -> None:
    """Clear a completed, cancelled, or fallback workflow transition."""

    resolved = WorkflowTransactionTarget(target)
    if resolved == WorkflowTransactionTarget.ADD_PICTURES:
        clear_add_pictures_editor_commit_request(state)
        return
    clear_pdf_editor_commit_request(state)
    if clear_export_job:
        reset_export_job(state)


def transaction_wait_copy(transaction: WorkflowTransaction) -> str:
    """Return calm user-facing wait copy for a transition."""

    if transaction.target == WorkflowTransactionTarget.ADD_PICTURES:
        return "Saving your latest itinerary edits before adding pictures…"
    return "Syncing the latest editor changes before PDF export…"


def transaction_timeout_copy(transaction: WorkflowTransaction) -> str:
    """Return calm user-facing timeout copy for a transition."""

    waited = int(transaction.elapsed_seconds)
    if transaction.target == WorkflowTransactionTarget.ADD_PICTURES:
        return f"The browser has not finished saving the latest itinerary edits after {waited} seconds."
    return f"The browser has not finished saving the latest PDF changes after {waited} seconds."

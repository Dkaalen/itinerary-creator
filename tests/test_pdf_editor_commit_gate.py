from __future__ import annotations

from app_modules.editor_commit import PDF_COMMIT_REQUEST_KEY
from app_modules.export_job_state import auto_pdf_create_requested
from app_modules.pdf_editor_commit_gate import (
    clear_pdf_editor_commit,
    pdf_editor_commit_pending,
    pdf_transaction_state,
    retry_pdf_editor_commit,
    start_pdf_editor_commit,
)
from app_modules.workflow_transactions import WorkflowTransactionStatus


def test_pdf_editor_commit_gate_starts_create_pdf_transaction() -> None:
    state: dict[str, object] = {}

    start_pdf_editor_commit(state, auto_create_pdf=True)
    transaction = pdf_transaction_state(state)

    assert transaction.status == WorkflowTransactionStatus.WAITING_FOR_BROWSER
    assert state[PDF_COMMIT_REQUEST_KEY] == transaction.commit_nonce
    assert pdf_editor_commit_pending(state) is True
    assert auto_pdf_create_requested(state) is True


def test_pdf_editor_commit_gate_clear_resets_pdf_transaction_and_auto_create() -> None:
    state: dict[str, object] = {}
    start_pdf_editor_commit(state, auto_create_pdf=True)

    clear_pdf_editor_commit(state)

    assert pdf_transaction_state(state).status == WorkflowTransactionStatus.IDLE
    assert pdf_editor_commit_pending(state) is False
    assert auto_pdf_create_requested(state) is False


def test_pdf_editor_commit_gate_retry_uses_fresh_nonce_without_clearing_auto_create() -> None:
    state: dict[str, object] = {}
    first = start_pdf_editor_commit(state, auto_create_pdf=True)

    second = retry_pdf_editor_commit(state, auto_create_pdf=True)

    assert second.status == WorkflowTransactionStatus.WAITING_FOR_BROWSER
    assert second.commit_nonce != first.commit_nonce
    assert auto_pdf_create_requested(state) is True
